from unittest import TestCase
import os
from api.views import create_external_task

class TestCreateTask(TestCase):
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    def test_createTask(self):
        #self.fail()
        #pass
        file=open(self.THIS_DIR)
        #create_external_task(xml, server)