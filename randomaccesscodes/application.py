from datetime import datetime
from random import randint
from uuid import NAMESPACE_URL, UUID, uuid5

from eventsourcing.application.simple import SimpleApplication
from eventsourcing.exceptions import RepositoryKeyError

from randomaccesscodes.domainmodel import ACCESS_CODES_RANGE, AccessCode
from randomaccesscodes.exceptions import (
    AccessCodeNotFound,
    AccessDenied,
    InvalidAccessTime,
    InvalidStatus,
    RevokeError,
)


class AccessCodesApplication(SimpleApplication):
    def issue_access_code(self, access_code_number: int, issued_on: datetime) -> None:
        try:
            access_code = self.get_access_code(access_code_number)
            access_code.recycle(issued_on)
        except AccessCodeNotFound:
            access_code_id = self.create_access_code_id(access_code_number)
            access_code = AccessCode.__create__(
                originator_id=access_code_id,
                access_code_number=access_code_number,
                issued_on=issued_on,
            )
        access_code.assert_status(AccessCode.STATUS_ISSUED)
        self.save(access_code)

    def authorise_access(self, access_code_number: int, accessed_on: datetime) -> None:
        try:
            access_code = self.get_access_code(access_code_number)
            access_code.authorise(accessed_on)
            self.save(access_code)
        except (AccessCodeNotFound, InvalidStatus, InvalidAccessTime):
            raise AccessDenied()

    def revoke_access(self, access_code_number: int) -> None:
        try:
            access_code = self.get_access_code(access_code_number)
            access_code.revoke()
            self.save(access_code)
        except AccessCodeNotFound:
            raise RevokeError()

    def get_access_code(self, access_code_number: int) -> AccessCode:
        access_code_id = self.create_access_code_id(access_code_number)
        try:
            access_code = self.repository[access_code_id]
        except RepositoryKeyError:
            raise AccessCodeNotFound(access_code_number)
        else:
            assert isinstance(access_code, AccessCode)
            return access_code

    @staticmethod
    def generate_access_code_number() -> int:
        return randint(*ACCESS_CODES_RANGE)

    @staticmethod
    def create_access_code_id(access_code_number) -> UUID:
        return uuid5(NAMESPACE_URL, f"/access_codes/{access_code_number}")
