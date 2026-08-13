''' Coordinate exclusive dual-GPU ownership between the resident realtime Qwen stack and Qwen3.6 evaluation. '''

import threading

class ModelRuntime:
    ''' Enforce single-interview access and exclusive evaluator ownership of the dual-GPU model worker. '''
    def __init__(self):
        ''' Track which interview or evaluation currently owns the process-wide model worker. '''
        self.lock = threading.RLock()
        self.active_interview_id = None
        self.evaluating = False
        self._suite = None

    @property
    def suite(self):
        ''' Delay heavy Qwen imports for non-server Django commands while sharing one RealModelSuite process-wide. '''
        if self._suite is None:
            from interviews.services.real_models import RealModelSuite  # noqa: PLC0415
            self._suite = RealModelSuite()

        return self._suite

    def preload_live(self):
        ''' Make every realtime Qwen model resident during Django server startup before interviews can be accepted. '''
        self.suite.load_live()

    def reserve_interview(self, interview_id):
        ''' Grant one browser interview exclusive use of the already-resident realtime Qwen stack. '''
        interview_id = str(interview_id)

        with self.lock:
            if self.evaluating or self.active_interview_id:
                return False

            if not self.suite.live_loaded():
                raise RuntimeError('Realtime interview models are not loaded.')

            self.active_interview_id = interview_id

        return True

    def release_interview(self, interview_id):
        ''' Return the realtime worker to available capacity after the matching browser disconnects. '''
        with self.lock:
            if self.active_interview_id == str(interview_id):
                self.active_interview_id = None

    def begin_evaluation(self, interview_id):
        ''' Transfer exclusive GPU ownership from a completed interview to Qwen3.6 final evaluation. '''
        interview_id = str(interview_id)

        with self.lock:
            if self.evaluating:
                return False

            if self.active_interview_id and self.active_interview_id != interview_id:
                return False

            self.active_interview_id = None
            self.evaluating = True

        loaded = False

        try:
            self.suite.load_evaluator()
            loaded = True

        finally:
            if not loaded:
                with self.lock:
                    self.evaluating = False

        return True

    def finish_evaluation(self):
        ''' Restore the realtime Qwen stack immediately after Qwen3.6 final evaluation releases the GPUs. '''
        try:
            self.suite.load_live()

        finally:
            with self.lock:
                self.evaluating = False

    def capacity_available(self):
        ''' Report whether the resident realtime stack is free for a new interview. '''
        with self.lock:
            return not self.evaluating and self.active_interview_id is None and self.suite.live_loaded()

model_runtime = ModelRuntime()
