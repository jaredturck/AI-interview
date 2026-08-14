''' Verify the resident Qwen3.5-9B loader keeps the simple single-GPU INT8 placement contract. '''

from unittest.mock import Mock

import pytest
import torch

from interviews.services import real_models


def test_shared_qwen_loader_uses_text_only_int8_sdpa(monkeypatch):
    ''' Verify Qwen3.5-9B loads as a text-only INT8 model entirely on GPU 0. '''
    tokenizer = Mock()
    model = Mock()
    tokenizer_loader = Mock(return_value=tokenizer)
    model_loader = Mock(return_value=model)
    processor_loader = Mock(side_effect=AssertionError('Qwen3.5-9B must not use AutoProcessor.'))
    monkeypatch.setattr(real_models.AutoTokenizer, 'from_pretrained', tokenizer_loader)
    monkeypatch.setattr(real_models.Qwen3_5ForCausalLM, 'from_pretrained', model_loader)
    monkeypatch.setattr(real_models.AutoProcessor, 'from_pretrained', processor_loader)

    real_models.QwenSharedModel()

    tokenizer_loader.assert_called_once_with(real_models.SHARED_MODEL)
    processor_loader.assert_not_called()
    model_loader.assert_called_once()
    args, kwargs = model_loader.call_args
    quantization = kwargs['quantization_config']
    assert args == (real_models.SHARED_MODEL,)
    assert real_models.SHARED_MODEL == 'Qwen/Qwen3.5-9B'
    assert kwargs['device_map'] == {'': 'cuda:0'}
    assert 'max_memory' not in kwargs
    assert kwargs['dtype'] == torch.float16
    assert kwargs['attn_implementation'] == 'sdpa'
    assert kwargs['low_cpu_mem_usage'] is True
    assert quantization.load_in_8bit is True
    assert quantization.load_in_4bit is False


def test_partial_preload_does_not_reload_resident_auxiliaries(monkeypatch):
    ''' Verify retrying after a shared-model failure keeps already resident auxiliary model instances. '''
    tts = Mock()
    asr = Mock()
    turn_detector = Mock()
    guard = Mock()
    misuse = Mock()
    shared = Mock()
    tts_loader = Mock(return_value=tts)
    asr_loader = Mock(return_value=asr)
    turn_loader = Mock(return_value=turn_detector)
    guard_loader = Mock(return_value=guard)
    misuse_loader = Mock(return_value=misuse)
    shared_loader = Mock(side_effect=[RuntimeError('shared model load failed'), shared])
    monkeypatch.setattr(real_models, 'load_qwen_tts', tts_loader)
    monkeypatch.setattr(real_models, 'QwenASRModel', asr_loader)
    monkeypatch.setattr(real_models, 'TurnDetector', turn_loader)
    monkeypatch.setattr(real_models, 'QwenGuardModel', guard_loader)
    monkeypatch.setattr(real_models, 'QwenTextModel', misuse_loader)
    monkeypatch.setattr(real_models, 'QwenSharedModel', shared_loader)
    suite = real_models.RealModelSuite()

    with pytest.raises(RuntimeError, match='shared model load failed'):
        suite.load_models()

    assert suite.models_loaded() is False
    suite.load_models()
    assert suite.models_loaded() is True
    assert tts_loader.call_count == 1
    assert asr_loader.call_count == 1
    assert turn_loader.call_count == 1
    assert guard_loader.call_count == 1
    assert misuse_loader.call_count == 1
    assert shared_loader.call_count == 2


def test_reliable_placement_and_evaluation_limits(monkeypatch):
    ''' Verify Qwen3.5-9B stays on GPU 0 while auxiliary language models remain on GPU 1. '''
    tokenizer = Mock()
    model = Mock()
    tokenizer_loader = Mock(return_value=tokenizer)
    model_loader = Mock(return_value=model)
    monkeypatch.setattr(real_models.AutoTokenizer, 'from_pretrained', tokenizer_loader)
    monkeypatch.setattr(real_models.AutoModelForCausalLM, 'from_pretrained', model_loader)

    real_models.QwenGuardModel()

    args, kwargs = model_loader.call_args
    assert args == (real_models.GUARD_MODEL,)
    assert kwargs['device_map'] == {'': 'cuda:1'}
    assert real_models.SHARED_MODEL_DEVICE == 'cuda:0'
    assert real_models.EVALUATOR_BATCH_SIZE == 2
    assert real_models.EVALUATOR_QUESTION_MAX_TOKENS == 512
    assert real_models.EVALUATOR_REASONING_MAX_TOKENS == 768
