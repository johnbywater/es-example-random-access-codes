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
from datetime import datetime, timedelta
from unittest import TestCase

from eventsourcing.application.notificationlog import NotificationLogReader
from eventsourcing.application.popo import PopoApplication

from randomaccesscodes.application import AccessCodesApplication
from randomaccesscodes.exceptions import AccessDenied, Unusable


class TestAccessCodes(TestCase):
    def test_issue_and_gain_access(self):
        with AccessCodesApplication.mixin(PopoApplication)() as app:
            app: AccessCodesApplication

            # Fail to gain access with invalid access code number.
            with self.assertRaises(AccessDenied):
                accessed_on = datetime.now()
                app.authorise_access(1000001, accessed_on)

            # Issue access code.
            issued_on = datetime.now()
            access_code_number = app.generate_access_code_number()
            app.issue_access_code(issued_on, access_code_number)
            self.assertIsInstance(access_code_number, int)

            # Gain access.
            accessed_on = datetime.now()
            app.authorise_access(access_code_number, accessed_on)

            # Fail to gain access twice.
            with self.assertRaises(AccessDenied):
                accessed_on = datetime.now()
                app.authorise_access(access_code_number, accessed_on)

    def test_issue_and_revoke_access(self):
        with AccessCodesApplication.mixin(PopoApplication)() as app:
            app: AccessCodesApplication

            # Fail to gain access with invalid access code number.
            with self.assertRaises(AccessDenied):
                accessed_on = datetime.now()
                app.authorise_access(1000001, accessed_on)

            # Issue access code.
            issued_on = datetime.now()
            access_code_number = app.generate_access_code_number()
            app.issue_access_code(issued_on, access_code_number)
            self.assertIsInstance(access_code_number, int)

            # Revoke access.
            app.revoke_access(access_code_number)

            # Fail to gain access.
            with self.assertRaises(AccessDenied):
                accessed_on = datetime.now()
                app.authorise_access(access_code_number, accessed_on)

    def test_issue_and_expire_access(self):
        with AccessCodesApplication.mixin(PopoApplication)() as app:
            app: AccessCodesApplication

            # Issue access code.
            issued_on = datetime.now()
            access_code_number = app.generate_access_code_number()
            app.issue_access_code(issued_on, access_code_number)

            # Fail to gain access after 48hrs.
            accessed_on = issued_on + timedelta(days=2)
            with self.assertRaises(AccessDenied):
                app.authorise_access(access_code_number, accessed_on)

    def test_issue_and_prevent_resuse_for_six_months(self):
        with AccessCodesApplication.mixin(PopoApplication)() as app:
            app: AccessCodesApplication

            # Issue access code.
            issued_on = datetime.now()
            access_code_number = app.generate_access_code_number()
            app.issue_access_code(issued_on, access_code_number)

            # Fail to issue same access code 100 days later.
            issued_on += timedelta(days=100)
            with self.assertRaises(Unusable):
                app.issue_access_code(issued_on, access_code_number)

            # Issue same access code 200 days later.
            issued_on += timedelta(days=200)
            app.issue_access_code(issued_on, access_code_number)

            # Gain access.
            accessed_on = issued_on + timedelta(hours=3)
            app.authorise_access(access_code_number, accessed_on)

            # Fail to gain access twice.
            with self.assertRaises(AccessDenied):
                app.authorise_access(access_code_number, accessed_on)

    def test_run_for_a_few_days(self):
        with AccessCodesApplication.mixin(PopoApplication)() as app:
            app: AccessCodesApplication

            num_days = 200
            num_access_codes_per_day = 1000
            started_on = datetime.now()
            for day in range(num_days):
                for _ in range(num_access_codes_per_day):
                    issued_on = started_on + timedelta(days=day)
                    while True:
                        access_code_number = app.generate_access_code_number()
                        try:
                            app.issue_access_code(issued_on, access_code_number)
                        except Unusable:
                            continue
                        else:
                            break

            reader = NotificationLogReader(app.notification_log)
            self.assertEqual(
                len(reader.read_list()), num_days * num_access_codes_per_day
            )
