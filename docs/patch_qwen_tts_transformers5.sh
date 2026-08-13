#!/usr/bin/env bash
set -euo pipefail

# Compatibility patch for qwen-tts 0.1.1 running with Transformers 5.15.0.
#
# This preserves the working single-environment setup used by this project:
# - removes the Transformers 4-only check_model_inputs decorator;
# - restores pad_token_id on the Qwen3 TTS configs;
# - restores the default RoPE implementation expected by Qwen3-TTS;
# - updates causal-mask calls to the Transformers 5.15 API.
#
# Dependencies must already be installed. The script intentionally refuses to
# patch other qwen-tts or Transformers versions because these edits are tied to
# the exact versions that were tested successfully.

if [[ -x './.venv/bin/python' ]]; then
    PYTHON_BIN='./.venv/bin/python'
else
    PYTHON_BIN="${PYTHON:-python3}"
fi

"$PYTHON_BIN" - <<'PY'
from importlib import metadata, util
from pathlib import Path
import ast
import shutil

EXPECTED_QWEN_TTS = '0.1.1'
EXPECTED_TRANSFORMERS = '5.15.0'

qwen_tts_version = metadata.version('qwen-tts')
transformers_version = metadata.version('transformers')

if qwen_tts_version != EXPECTED_QWEN_TTS:
    raise SystemExit(f'Expected qwen-tts {EXPECTED_QWEN_TTS}, found {qwen_tts_version}. Refusing to patch an unverified version.')

if transformers_version != EXPECTED_TRANSFORMERS:
    raise SystemExit(f'Expected transformers {EXPECTED_TRANSFORMERS}, found {transformers_version}. Refusing to patch an unverified version.')

spec = util.find_spec('qwen_tts')
if spec is None or not spec.submodule_search_locations:
    raise SystemExit('Could not locate the installed qwen_tts package.')

package_root = Path(next(iter(spec.submodule_search_locations)))
config_path = package_root / 'core/models/configuration_qwen3_tts.py'
model_path = package_root / 'core/models/modeling_qwen3_tts.py'
tokenizer_path = package_root / 'core/tokenizer_12hz/modeling_qwen3_tts_tokenizer_v2.py'
paths = [config_path, model_path, tokenizer_path]

for path in paths:
    if not path.is_file():
        raise SystemExit(f'Expected qwen-tts source file not found: {path}')

for path in paths:
    backup = path.with_suffix(path.suffix + '.bak_qwen_tf5')
    if not backup.exists():
        shutil.copy2(path, backup)


def patch_check_model_inputs(text):
    old_import = 'from transformers.utils.generic import check_model_inputs\n'
    old_decorator = '    @check_model_inputs()\n'
    has_import = old_import in text
    has_decorator = old_decorator in text

    if has_import != has_decorator:
        raise SystemExit('Found a partial check_model_inputs patch; refusing to guess the source state.')

    if has_import:
        text = text.replace(old_import, '', 1)
        text = text.replace(old_decorator, '', 1)
        print('Patched removed Transformers check_model_inputs API.')
    else:
        print('check_model_inputs compatibility patch already present.')

    return text


def is_pad_assignment(node):
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == 'self'
        and node.attr == 'pad_token_id'
        and isinstance(node.ctx, ast.Store)
    )


def is_super_init(statement):
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return False

    function = statement.value.func
    return (
        isinstance(function, ast.Attribute)
        and function.attr == '__init__'
        and isinstance(function.value, ast.Call)
        and isinstance(function.value.func, ast.Name)
        and function.value.func.id == 'super'
    )


def patch_pad_token_id(text):
    tree = ast.parse(text)
    class_names = {'Qwen3TTSTalkerConfig', 'Qwen3TTSTalkerCodePredictorConfig'}
    found_classes = set()
    insertions = []

    for class_node in tree.body:
        if not isinstance(class_node, ast.ClassDef) or class_node.name not in class_names:
            continue

        found_classes.add(class_node.name)
        init = next((node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == '__init__'), None)

        if init is None:
            raise SystemExit(f'No __init__ found in {class_node.name}.')

        if init.args.kwarg is None or init.args.kwarg.arg != 'kwargs':
            raise SystemExit(f'Expected **kwargs in {class_node.name}.__init__.')

        if any(is_pad_assignment(node) for node in ast.walk(init)):
            print(f'pad_token_id compatibility patch already present in {class_node.name}.')
            continue

        super_init = next((statement for statement in init.body if is_super_init(statement)), None)
        if super_init is None:
            raise SystemExit(f'Expected super().__init__ call not found in {class_node.name}.')

        insertions.append((super_init.end_lineno, class_node.name))

    missing = class_names - found_classes
    if missing:
        raise SystemExit(f'Expected Qwen TTS config classes not found: {sorted(missing)}')

    if not insertions:
        return text

    lines = text.splitlines(keepends=True)
    for line_number, class_name in sorted(insertions, reverse=True):
        lines.insert(line_number, "        self.pad_token_id = kwargs.get('pad_token_id')\n")
        print(f'Restored pad_token_id on {class_name}.')

    return ''.join(lines)


ROPE_HELPER = '''\n\ndef _compute_default_rope_parameters(config, device=None, seq_len=None):\n    base = config.rope_theta\n    partial_rotary_factor = getattr(config, 'partial_rotary_factor', 1.0)\n    head_dim = getattr(config, 'head_dim', None) or config.hidden_size // config.num_attention_heads\n    dim = int(head_dim * partial_rotary_factor)\n    inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2, dtype=torch.int64).to(device=device, dtype=torch.float) / dim))\n    return inv_freq, 1.0\n'''


def patch_rope(text, expected_lookups, label):
    helper_name = 'def _compute_default_rope_parameters('
    old = 'self.rope_init_fn = ROPE_INIT_FUNCTIONS[self.rope_type]'
    new = "self.rope_init_fn = _compute_default_rope_parameters if self.rope_type == 'default' else ROPE_INIT_FUNCTIONS[self.rope_type]"

    old_count = text.count(old)

    if old_count:
        if old_count != expected_lookups:
            raise SystemExit(f'Expected {expected_lookups} default RoPE lookups in {label}, found {old_count}.')

        if helper_name not in text:
            marker = 'logger = logging.get_logger(__name__)\n'
            if text.count(marker) != 1:
                raise SystemExit(f'Expected one logger insertion point in {label}.')
            text = text.replace(marker, marker + ROPE_HELPER, 1)

        text = text.replace(old, new)
        print(f'Patched {expected_lookups} default RoPE lookup(s) in {label}.')
        return text

    if helper_name in text and text.count('_compute_default_rope_parameters if self.rope_type') == expected_lookups:
        print(f'Default RoPE compatibility patch already present in {label}.')
        return text

    raise SystemExit(f'Could not recognize the RoPE source state in {label}. Refusing to patch.')


def replace_block(text, old, new, label):
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 1 and new_count == 0:
        print(f'Patched {label}.')
        return text.replace(old, new, 1)

    if old_count == 0 and new_count == 1:
        print(f'{label} already patched.')
        return text

    raise SystemExit(f'Could not recognize source state for {label}. Refusing to patch.')


config_text = config_path.read_text()
model_text = model_path.read_text()
tokenizer_text = tokenizer_path.read_text()

tokenizer_text = patch_check_model_inputs(tokenizer_text)
config_text = patch_pad_token_id(config_text)
model_text = patch_rope(model_text, 2, 'modeling_qwen3_tts.py')
tokenizer_text = patch_rope(tokenizer_text, 1, 'modeling_qwen3_tts_tokenizer_v2.py')

model_mask_old = '''            mask_kwargs = {\n                "config": self.config,\n                "input_embeds": inputs_embeds,\n                "attention_mask": attention_mask,\n                "cache_position": cache_position,\n                "past_key_values": past_key_values,\n            }'''
model_mask_new = '''            mask_kwargs = {\n                "config": self.config,\n                "inputs_embeds": inputs_embeds,\n                "attention_mask": attention_mask,\n                "past_key_values": past_key_values,\n                "position_ids": position_ids,\n            }'''
model_text = replace_block(
    model_text,
    model_mask_old,
    model_mask_new,
    'Qwen3TTSTalkerCodePredictorModel causal-mask arguments',
)

talker_mask_old = '''        causal_mask = mask_function(\n            config=self.config,\n            input_embeds=inputs_embeds,\n            attention_mask=attention_mask,\n            cache_position=cache_position,\n            past_key_values=past_key_values,\n            position_ids=text_position_ids,\n        )'''
talker_mask_new = '''        causal_mask = mask_function(\n            config=self.config,\n            inputs_embeds=inputs_embeds,\n            attention_mask=attention_mask,\n            past_key_values=past_key_values,\n            position_ids=text_position_ids,\n        )'''
model_text = replace_block(
    model_text,
    talker_mask_old,
    talker_mask_new,
    'Qwen3TTSTalkerModel causal-mask arguments',
)

tokenizer_mask_old = '''            mask_kwargs = {\n                "config": self.config,\n                "input_embeds": inputs_embeds,\n                "attention_mask": attention_mask,\n                "cache_position": cache_position,\n                "past_key_values": past_key_values,\n                "position_ids": position_ids,\n            }'''
tokenizer_mask_new = '''            mask_kwargs = {\n                "config": self.config,\n                "inputs_embeds": inputs_embeds,\n                "attention_mask": attention_mask,\n                "past_key_values": past_key_values,\n                "position_ids": position_ids,\n            }'''
tokenizer_text = replace_block(
    tokenizer_text,
    tokenizer_mask_old,
    tokenizer_mask_new,
    'Qwen3TTSTokenizerV2DecoderTransformerModel causal-mask arguments',
)

for path, text in [
    (config_path, config_text),
    (model_path, model_text),
    (tokenizer_path, tokenizer_text),
]:
    ast.parse(text)
    path.write_text(text)

print()
print('Qwen TTS Transformers 5 compatibility patch complete.')
print(f'qwen-tts:    {qwen_tts_version}')
print(f'transformers: {transformers_version}')
print(f'package:      {package_root}')
print('Backups use the .bak_qwen_tf5 suffix and are never overwritten.')
PY

printf '\nPatch finished successfully. Run npm run dev to validate full realtime model loading.\n'
