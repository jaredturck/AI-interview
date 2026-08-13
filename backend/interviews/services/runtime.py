import importlib
import threading

from ai_interviewer.runtime_config import RUNTIME
from interviews.services.mock_models import MockModelSuite


class ModelRuntime:
    def __init__(self):
        self.lock = threading.RLock()
        self.active_interview_id = None
        self.evaluating = False
        self.connections = {}
        self.suite = self.create_suite()

    def create_suite(self):
        if RUNTIME["models"]["mode"] == "mock":
            return MockModelSuite()
        module = importlib.import_module("interviews.services.real_models")
        return module.RealModelSuite()

    def reserve_interview(self, interview_id):
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
        interview_id = str(interview_id)
        with self.lock:
            self.connections[interview_id] = self.connections.get(interview_id, 0) + 1

    def remove_connection(self, interview_id):
        interview_id = str(interview_id)
        with self.lock:
            count = self.connections.get(interview_id, 0) - 1
            if count > 0:
                self.connections[interview_id] = count
            else:
                self.connections.pop(interview_id, None)

    def has_connection(self, interview_id):
        with self.lock:
            return self.connections.get(str(interview_id), 0) > 0

    def release_interview(self, interview_id):
        with self.lock:
            if self.active_interview_id == str(interview_id):
                self.active_interview_id = None

    def begin_evaluation(self, interview_id):
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
        with self.lock:
            return not self.evaluating and self.active_interview_id is None


model_runtime = ModelRuntime()
