from datetime import datetime, timedelta

from eventsourcing.domain.model.aggregate import BaseAggregateRoot

from randomaccesscodes.exceptions import InvalidAccessTime, InvalidStatus, RecycleError

ACCESS_CODES_RANGE = (1000000, 1999999)
ACCESS_PERIOD = 1
RECYCLE_PERIOD = 180


class AccessCode(BaseAggregateRoot):
    __subclassevents__ = True
    STATUS_ISSUED = "ISSUED"
    STATUS_USED = "USED"
    STATUS_REVOKED = "REVOKED"

    def __init__(self, access_code_number: int, issued_on: datetime, **kwargs):
        super(AccessCode, self).__init__(**kwargs)
        self.access_code_number: int = access_code_number
        self.status: str = AccessCode.STATUS_ISSUED
        self.issued_on: datetime = issued_on

    def authorise(self, accessed_on: datetime) -> None:
        self.assert_status(AccessCode.STATUS_ISSUED)
        self.validate_access_time(accessed_on)
        self.__trigger_event__(self.Authorised)

    class Authorised(BaseAggregateRoot.Event):
        def mutate(self, obj: "AccessCode"):
            obj.status = AccessCode.STATUS_USED

    def revoke(self) -> None:
        self.__trigger_event__(self.Revoked)

    class Revoked(BaseAggregateRoot.Event):
        def mutate(self, obj: "AccessCode"):
            obj.status = AccessCode.STATUS_REVOKED

    def recycle(self, issued_on: datetime) -> None:
        if issued_on < self.issued_on + timedelta(days=RECYCLE_PERIOD):
            raise RecycleError()
        self.__trigger_event__(self.Recycled, issued_on=issued_on)

    class Recycled(BaseAggregateRoot.Event):
        def mutate(self, obj: "AccessCode"):
            obj.status = AccessCode.STATUS_ISSUED
            obj.issued_on = self.issued_on

        @property
        def issued_on(self):
            return self.__dict__["issued_on"]

    def validate_access_time(self, accessed_on: datetime) -> None:
        if accessed_on > self.issued_on + timedelta(days=ACCESS_PERIOD):
            raise InvalidAccessTime()

    def assert_status(self, required_status: str):
        if self.status != required_status:
            raise InvalidStatus(
                "Status is %s but required to be %s" % (self.status, required_status)
            )
