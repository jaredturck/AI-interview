''' Isolate final Qwen3.6 evaluation from Django CUDA state while collecting worker results for persistence. '''

import multiprocessing, queue

from interviews.services.evaluator_worker import run_evaluator_worker

EVALUATOR_SHUTDOWN_SECONDS = 60

def evaluate_in_worker(job_description, transcript, questions):
    ''' Run one clean vLLM evaluator process and return its criterion answers plus final decision. '''
    context = multiprocessing.get_context('spawn')
    result_queue = context.Queue()
    process = context.Process(target=run_evaluator_worker, args=(job_description, transcript, questions, result_queue))
    process.start()
    answers = []
    result = ''
    error = ''
    terminal_event = False
    shutdown_failed = False

    try:
        while not terminal_event:
            try:
                event = result_queue.get(timeout=1)

            except queue.Empty:
                if process.is_alive():
                    continue

                break

            event_type = event.get('type')

            if event_type == 'result':
                answers = event.get('answers') or []
                result = event.get('result') or ''
                terminal_event = True
            elif event_type == 'error':
                error = event.get('message') or 'unknown evaluator error'
                terminal_event = True

    finally:
        process.join(timeout=EVALUATOR_SHUTDOWN_SECONDS)

        if process.is_alive():
            shutdown_failed = True
            process.terminate()
            process.join()

        result_queue.close()

    if shutdown_failed:
        error = 'Evaluator process did not shut down cleanly.'
    elif not terminal_event:
        error = f'Evaluator process exited with code {process.exitcode}.'

    return {'answers': answers, 'result': result, 'error': error}
