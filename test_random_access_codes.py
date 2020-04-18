# https://github.com/ylorph/The-Inevitable-Event-Centric-Book/issues/47
#
# You must assign a unique access code in a (pseudo) random fashion.
# The range of access code at your disposal is [1 000 000, 1 999 999]
# The access code will be used to give you access to the system at a certain day
#   - [issued, valid for next 24hrs, "usage" of a code starts here]
# Once an access code is used , it can not be reused for 6 months.
#   - [after access, it's "unusable" for 6 months]
# An assigned access code, giving access in the future, may be revoked at any time.
#   - [if issued, can be revoked]
#   - [after revoked, it's "unusable" for 6 months]
# It is foreseen that up to 1 000 access codes will be used per day.
#   - [360 / 2 => 180 days, * 1000 per day => 180,000 access codes in use at any time < 1M]
#
# Solve this in an Event Sourced fashion.
# Bonus point if the assignment of the access code does not suffer from Eventual Consistency
#
from datetime import datetime, timedelta
from unittest import TestCase

from eventsourcing.application.notificationlog import NotificationLogReader
from eventsourcing.application.popo import PopoApplication

from randomaccesscodes.application import AccessCodesApplication
from randomaccesscodes.exceptions import AccessDenied, RevokeError, RecycleError


class TestAccessCodes(TestCase):
    def setUp(self) -> None:
        self.app = AccessCodesApplication.mixin(infrastructure_class=PopoApplication)()

    def tearDown(self) -> None:
        self.app.close()

    def test_invalid_access_code_denied(self):
        # Fail to gain access with invalid access code number.
        with self.assertRaises(AccessDenied):
            accessed_on = datetime.now()
            self.app.authorise_access(1000001, accessed_on)

    def test_issue_and_gain_access(self):
        # Issue access code.
        access_code_number = self.app.generate_access_code_number()
        issued_on = datetime.now()
        self.app.issue_access_code(access_code_number, issued_on)

        # Gain access.
        accessed_on = datetime.now()
        self.app.authorise_access(access_code_number, accessed_on)

        # Fail to gain access twice.
        with self.assertRaises(AccessDenied):
            accessed_on = datetime.now()
            self.app.authorise_access(access_code_number, accessed_on)

    def test_issue_and_revoke_access(self):
        # Fail to gain access with invalid access code number.
        with self.assertRaises(AccessDenied):
            accessed_on = datetime.now()
            self.app.authorise_access(1000001, accessed_on)

        # Issue access code.
        access_code_number = self.app.generate_access_code_number()
        issued_on = datetime.now()
        self.app.issue_access_code(access_code_number, issued_on)

        # Revoke access.
        self.app.revoke_access(access_code_number)

        # Fail to gain access.
        with self.assertRaises(AccessDenied):
            accessed_on = datetime.now()
            self.app.authorise_access(access_code_number, accessed_on)

    def test_revoke_invalid_access_code(self):
        # Fail to revoke access code.
        with self.assertRaises(RevokeError):
            self.app.revoke_access(1000001)

    def test_issue_and_expire(self):
        # Issue access code.
        access_code_number = self.app.generate_access_code_number()
        issued_on = datetime.now()
        self.app.issue_access_code(access_code_number, issued_on)

        # Fail to gain access after 48hrs.
        accessed_on = issued_on + timedelta(days=2)
        with self.assertRaises(AccessDenied):
            self.app.authorise_access(access_code_number, accessed_on)

    def test_issue_and_prevent_reuse_for_six_months(self):
        # Issue access code.
        access_code_number = self.app.generate_access_code_number()
        issued_on = datetime.now()
        self.app.issue_access_code(access_code_number, issued_on)

        # Fail to issue same access code 100 days later.
        issued_on += timedelta(days=100)
        with self.assertRaises(RecycleError):
            self.app.issue_access_code(access_code_number, issued_on)

        # Issue same access code 200 days later.
        issued_on += timedelta(days=200)
        self.app.issue_access_code(access_code_number, issued_on)

        # Gain access.
        accessed_on = issued_on + timedelta(hours=3)
        self.app.authorise_access(access_code_number, accessed_on)

        # Fail to gain access twice.
        with self.assertRaises(AccessDenied):
            self.app.authorise_access(access_code_number, accessed_on)

    def test_run_for_a_few_days(self):
        num_days = 200
        num_access_codes_per_day = 1000
        started_on = datetime.now()
        for day in range(num_days):
            for _ in range(num_access_codes_per_day):
                issued_on = started_on + timedelta(days=day)
                while True:
                    access_code_number = self.app.generate_access_code_number()
                    try:
                        self.app.issue_access_code(access_code_number, issued_on)
                    except RecycleError:
                        continue
                    else:
                        break

        reader = NotificationLogReader(self.app.notification_log)
        self.assertEqual(len(reader.read_list()), num_days * num_access_codes_per_day)
