''' Coordinate exclusive GPU ownership between live interviewing and evaluation. '''

import threading

class ModelRuntime:
    ''' Manage the single dual-GPU interview and evaluation worker. '''
    def __init__(self):
        ''' Initialize process-wide model ownership state. '''
        self.lock = threading.RLock()
        self.active_interview_id = None
        self.evaluating = False
        self._suite = None

    @property
    def suite(self):
        ''' Return the lazily created real model suite. '''
        if self._suite is None:
            from interviews.services.real_models import RealModelSuite  # noqa: PLC0415
            self._suite = RealModelSuite()

        return self._suite

    def reserve_interview(self, interview_id):
        ''' Reserve the live model worker for one browser connection. '''
        interview_id = str(interview_id)

        with self.lock:
            if self.evaluating or self.active_interview_id:
                return False

            self.active_interview_id = interview_id

        loaded = False

        try:
            self.suite.load_live()
            loaded = True

        finally:
            if not loaded:
                self.release_interview(interview_id)

        return True

    def release_interview(self, interview_id):
        ''' Release a disconnected live interview reservation. '''
        with self.lock:
            if self.active_interview_id == str(interview_id):
                self.active_interview_id = None

    def begin_evaluation(self, interview_id):
        ''' Atomically hand the GPU worker from an interview to the evaluator. '''
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
        ''' Release the evaluator and return the worker to an idle state. '''
        self.suite.unload_evaluator()

        with self.lock:
            self.evaluating = False

    def capacity_available(self):
        ''' Return whether a new interview can reserve the GPU worker. '''
        with self.lock:
            return not self.evaluating and self.active_interview_id is None

model_runtime = ModelRuntime()
