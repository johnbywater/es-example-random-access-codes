from random import randint
from uuid import NAMESPACE_URL, uuid5

from eventsourcing.application.simple import SimpleApplication
from eventsourcing.exceptions import RepositoryKeyError

from randomaccesscodes.domainmodel import AccessCode
from randomaccesscodes.exceptions import AccessDenied, InvalidAccessTime, InvalidStatus


class AccessCodesApplication(SimpleApplication):
    def generate_access_code_number(self):
        return randint(1000000, 1999999)

    def issue_access_code(self, issued_on, access_code_number):
        try:
            access_code = self.get_access_code(access_code_number)
            access_code.recycle(issued_on)
        except RepositoryKeyError:
            access_code_id = self.create_access_code_id(access_code_number)
            access_code = AccessCode.__create__(
                originator_id=access_code_id,
                access_code_number=access_code_number,
                issued_on=issued_on,
            )
        access_code.assert_status(AccessCode.STATUS_ISSUED)
        self.save(access_code)

    def authorise_access(self, access_code_number, accessed_on):
        try:
            access_code = self.get_access_code(access_code_number)
            access_code.authorise(accessed_on)
            self.save(access_code)
        except (RepositoryKeyError, InvalidStatus, InvalidAccessTime):
            raise AccessDenied()

    def revoke_access(self, access_code_number):
        try:
            access_code = self.get_access_code(access_code_number)
            access_code.revoke()
            self.save(access_code)
        except (RepositoryKeyError, InvalidStatus):
            raise AccessDenied()

    def get_access_code(self, access_code_number) -> AccessCode:
        access_code_id = self.create_access_code_id(access_code_number)
        access_code = self.repository[access_code_id]
        assert isinstance(access_code, AccessCode)
        return access_code

    def create_access_code_id(self, access_code_number):
        return uuid5(NAMESPACE_URL, "/access_codes/%d" % access_code_number)
