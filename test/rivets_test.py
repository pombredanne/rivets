import os
import sys

if sys.version_info[:2] == (2,6):
	import unittest2 as unittest
else:
	import unittest

import shutil

class RivetsTest(unittest.TestCase):

	FIXTURE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),'fixtures'))

	def fixture(self,path):
		return open(self.fixture_path(path)).read()

	def fixture_path(self,path):
		if path == self.FIXTURE_ROOT:
			return path
		else:
			return os.path.join(self.FIXTURE_ROOT,path)

	def sandbox(self,*paths,**kwargs):
		backup_paths = []
		remove_paths = []

		callback = kwargs.pop('callback',None)

		for path in paths:
			if os.path.exists(path):
				backup_paths.append(path)
			else:
				remove_paths.append(path)

		try:
			for path in backup_paths:
				shutil.copy2(path,"%s.orig"%path) if os.path.isfile(path) else shutil.copytree(path)

			return callback()

		finally:
			for path in backup_paths:
				if os.path.exists("%s.orig"%path):
					shutil.move("%s.orig"%path,path)

				assert not os.path.exists("%s.orig"%path)

			for path in remove_paths:
				if os.path.exists(path):
					os.remove(path) if os.path.isfile(path) else os.rmdir(path)

				assert not os.path.exists(path)