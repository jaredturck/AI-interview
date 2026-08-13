''' Coordinate exclusive GPU ownership between live interviewing and evaluation. '''
import importlib, threading

from ai_interviewer.runtime_config import RUNTIME
from interviews.services.mock_models import MockModelSuite

class ModelRuntime:
    ''' Manage the single dual-GPU interview and evaluation worker. '''
    def __init__(self):
        ''' Initialize process-wide model ownership state. '''
        self.lock = threading.RLock()
        self.active_interview_id = None
        self.evaluating = False
        self.connections = {}
        self.suite = self.create_suite()

    def create_suite(self):
        ''' Create either the lightweight mock suite or real Qwen suite. '''
        if RUNTIME['models']['mode'] == 'mock':
            return MockModelSuite()

        module = importlib.import_module('interviews.services.real_models')
        return module.RealModelSuite()

    def reserve_interview(self, interview_id):
        ''' Reserve the live model worker for one interview session. '''
        interview_id = str(interview_id)

        with self.lock:
            if self.evaluating:
                return False

            if self.active_interview_id == interview_id:
                return True

            if self.active_interview_id:
                return False

            self.active_interview_id = interview_id

        loaded = False

        try:
            self.suite.load_live()
            loaded = True

        finally:
            if not loaded:
                with self.lock:
                    if self.active_interview_id == interview_id:
                        self.active_interview_id = None

        return True

    def add_connection(self, interview_id):
        ''' Record one active browser connection for an interview. '''
        interview_id = str(interview_id)

        with self.lock:
            self.connections[interview_id] = self.connections.get(interview_id, 0) + 1

    def remove_connection(self, interview_id):
        ''' Remove one browser connection from an interview. '''
        interview_id = str(interview_id)

        with self.lock:
            count = self.connections.get(interview_id, 0) - 1

            if count > 0:
                self.connections[interview_id] = count
            else:
                self.connections.pop(interview_id, None)

    def has_connection(self, interview_id):
        ''' Return whether an interview still has a connected browser. '''
        with self.lock:
            return self.connections.get(str(interview_id), 0) > 0

    def release_interview(self, interview_id):
        ''' Release a live interview reservation without unloading models. '''
        with self.lock:
            if self.active_interview_id == str(interview_id):
                self.active_interview_id = None

    def begin_evaluation(self, interview_id):
        ''' Atomically hand the worker from an interview to the evaluator. '''
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
        ''' Return the GPU worker to live interview mode after evaluation. '''
        self.suite.unload_evaluator()
        loaded = False

        try:
            self.suite.load_live()
            loaded = True

        finally:
            with self.lock:
                self.evaluating = False

        return loaded

    def capacity_available(self):
        ''' Return whether a new interview can reserve the worker. '''
        with self.lock:
            return not self.evaluating and self.active_interview_id is None

model_runtime = ModelRuntime()
