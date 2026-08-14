''' Coordinate serialized inference over one permanently resident dual-GPU model stack. '''

import threading

class ModelRuntime:
    ''' Enforce one active interview or evaluation while every model remains resident on the worker GPUs. '''
    def __init__(self):
        ''' Track which interview or evaluation currently owns inference on the process-wide model suite. '''
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

    def preload_models(self):
        ''' Make the complete interview/evaluation model stack resident during Django server startup. '''
        self.suite.load_models()

    def reserve_interview(self, interview_id):
        ''' Grant one browser interview exclusive inference access without unloading any resident model. '''
        interview_id = str(interview_id)

        with self.lock:
            if self.evaluating or self.active_interview_id:
                return False

            if not self.suite.models_loaded():
                self.suite.load_models()

            self.active_interview_id = interview_id

        return True

    def release_interview(self, interview_id):
        ''' Return inference capacity after the matching browser disconnects while leaving every model resident. '''
        with self.lock:
            if self.active_interview_id == str(interview_id):
                self.active_interview_id = None

    def begin_evaluation(self, interview_id):
        ''' Transfer serialized inference ownership from the completed interview to resident Qwen3.5-9B evaluation. '''
        interview_id = str(interview_id)

        with self.lock:
            if self.evaluating:
                return False

            if self.active_interview_id and self.active_interview_id != interview_id:
                return False

            if not self.suite.models_loaded():
                self.suite.load_models()

            self.active_interview_id = None
            self.evaluating = True

        return True

    def finish_evaluation(self):
        ''' Release evaluation ownership without changing GPU model residency. '''
        with self.lock:
            self.evaluating = False

    def generate_job_metadata(self, description):
        ''' Generate concise job title metadata only while the shared inference worker is otherwise free. '''
        with self.lock:
            if self.evaluating or self.active_interview_id:
                return ''

            if not self.suite.models_loaded():
                self.suite.load_models()

            return self.suite.job_metadata(description)

    def capacity_available(self):
        ''' Report whether the shared resident model worker is free for a new interview. '''
        with self.lock:
            return not self.evaluating and self.active_interview_id is None

model_runtime = ModelRuntime()
