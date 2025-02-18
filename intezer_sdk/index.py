import time
from http import HTTPStatus

from intezer_sdk import consts
from intezer_sdk import errors
from intezer_sdk.api import IntezerApi
from intezer_sdk.api import get_global_api


class Index(object):
    def __init__(self,
                 index_as: consts.IndexType,
                 file_path: str = None,
                 sha256: str = None,
                 api: IntezerApi = None,
                 family_name: str = None):
        if (sha256 is not None) == (file_path is not None):
            raise ValueError('Choose between sha256 or file indexing')

        if index_as == consts.IndexType.MALICIOUS and family_name is None:
            raise ValueError('family_name is mandatory if the index type is malicious')

        self.status = None
        self.index_id = None
        self._sha256 = sha256
        self._file_path = file_path
        self._api = api or get_global_api()
        self._index_as = index_as
        self._family_name = family_name

    def send(self, wait: bool = False):
        if self.index_id:
            raise errors.IndexHasAlreadyBeenSent()

        if self._sha256:
            self.index_id = self._api.index_by_sha256(self._sha256, self._index_as, self._family_name)
        else:
            self.index_id = self._api.index_by_file(self._file_path, self._index_as, self._family_name)

        self.status = consts.IndexStatusCode.CREATED

        if wait:
            self.wait_for_completion()

    def wait_for_completion(self):
        if self._is_index_operation_running():
            status_code = self.check_status()

            while status_code != consts.IndexStatusCode.FINISH:
                time.sleep(consts.CHECK_STATUS_INTERVAL)
                status_code = self.check_status()

    def check_status(self):
        if not self._is_index_operation_running():
            raise errors.IntezerError('Index operation isn\'t currently running')

        response = self._api.get_index_response(self.index_id)
        if response.status_code == HTTPStatus.OK:
            if response.json()['status'] == 'failed':
                raise errors.IndexFailed()
            else:
                self.status = consts.IndexStatusCode.FINISH
        elif response.status_code == HTTPStatus.ACCEPTED:
            self.status = consts.IndexStatusCode.IN_PROGRESS
        else:
            raise errors.IntezerError('Error in response status code:{}'.format(response.status_code))

        return self.status

    def _is_index_operation_running(self):
        return self.status in (consts.IndexStatusCode.CREATED, consts.IndexStatusCode.IN_PROGRESS)
