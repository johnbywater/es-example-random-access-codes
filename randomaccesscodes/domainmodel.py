from datetime import timedelta

from eventsourcing.domain.model.aggregate import BaseAggregateRoot

from randomaccesscodes.exceptions import InvalidAccessTime, InvalidStatus, Unusable


class AccessCode(BaseAggregateRoot):
    STATUS_ISSUED = "ISSUED"
    STATUS_USED = "USED"
    STATUS_REVOKED = "REVOKED"

    def __init__(self, access_code_number, issued_on, **kwargs):
        super(AccessCode, self).__init__(**kwargs)
        self.access_code_number = access_code_number
        self.status = AccessCode.STATUS_ISSUED
        self.issued_on = issued_on

    def authorise(self, accessed_on):
        self.assert_status(AccessCode.STATUS_ISSUED)
        self.validate_access_time(accessed_on)
        self.__trigger_event__(self.Authorised)

    class Authorised(BaseAggregateRoot.Event):
        def mutate(self, obj: "AccessCode"):
            obj.status = AccessCode.STATUS_USED

    def revoke(self):
        self.assert_status(AccessCode.STATUS_ISSUED)
        self.__trigger_event__(self.Revoked)

    class Revoked(BaseAggregateRoot.Event):
        def mutate(self, obj: "AccessCode"):
            obj.status = AccessCode.STATUS_REVOKED

    def recycle(self, issued_on):
        if issued_on < self.issued_on + timedelta(days=180):
            raise Unusable()
        self.__trigger_event__(self.Recycled, issued_on=issued_on)

    class Recycled(BaseAggregateRoot.Event):
        def mutate(self, obj: "AccessCode"):
            obj.status = AccessCode.STATUS_ISSUED
            obj.issued_on = self.issued_on

        @property
        def issued_on(self):
            return self.__dict__["issued_on"]

    def validate_access_time(self, accessed_on):
        if accessed_on > self.issued_on + timedelta(days=1):
            raise InvalidAccessTime()

    def assert_status(self, required_status):
        if self.status != required_status:
            raise InvalidStatus(
                "Status is %s but required to be %s" % (self.status, required_status)
            )
