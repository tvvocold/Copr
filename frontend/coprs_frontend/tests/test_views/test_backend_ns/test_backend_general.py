import json

from coprs.signals import build_finished
from tests.coprs_test_case import CoprsTestCase


class TestWaitingBuilds(CoprsTestCase):

    def test_no_waiting_builds(self):
        assert '"builds": []' in self.tc.get(
            "/backend/waiting/", headers=self.auth_header).data

    def test_waiting_build_only_lists_not_started_or_ended(
            self, f_users, f_coprs, f_mock_chroots, f_builds, f_db):

        r = self.tc.get("/backend/waiting/", headers=self.auth_header)
        assert len(json.loads(r.data)["builds"]) == 5


# status = 0 # failure
# status = 1 # succeeded
class TestUpdateBuilds(CoprsTestCase):
    data1 = """
{
  "builds":[
   {
     "id": 1,
     "copr_id": 2,
     "results": "http://server/results/foo/bar/",
     "started_on": 139086644000
   }
  ]
}"""

    data2 = """
{
  "builds":[
   {
     "id": 1,
     "copr_id": 2,
     "status": 1,
     "chroot": "fedora-18-x86_64",
     "ended_on": 139086644000
   }
  ]
}"""

    data3 = """
{
  "builds":[
   {
     "id": 1,
     "copr_id": 2,
     "started_on": 139086644000
   },
   {
     "id": 2,
     "copr_id": 1,
     "status": 0,
     "chroot": "fedora-18-x86_64",
     "results": "http://server/results/foo/bar/",
     "ended_on": 139086644000
   },
   {
     "id": 123321,
     "copr_id": 1,
     "status": 0,
     "ended_on": 139086644000
   },
   {
     "id": 1234321,
     "copr_id": 2,
     "results": "http://server/results/foo/bar/",
     "started_on": 139086644000
   }
  ]
}"""

    def test_updating_requires_password(self, f_users, f_coprs, f_builds, f_db):
        r = self.tc.post("/backend/update/",
                         content_type="application/json",
                         data="")
        assert "You have to provide the correct password" in r.data

    def test_update_build_started(self, f_users, f_coprs, f_builds, f_db):
        self.b1.started_on = None
        self.db.session.add(self.b1)
        self.db.session.commit()

        r = self.tc.post("/backend/update/",
                         content_type="application/json",
                         headers=self.auth_header,
                         data=self.data1)
        assert json.loads(r.data)["updated_builds_ids"] == [1]
        assert json.loads(r.data)["non_existing_builds_ids"] == []

        updated = self.models.Build.query.filter(
            self.models.Build.id == 1).first()
        assert updated.results == "http://server/results/foo/bar/"
        assert updated.started_on == 139086644000

    def test_update_build_ended(self, f_users, f_coprs, f_mock_chroots,
                                f_builds, f_db):

        r = self.tc.post("/backend/update/",
                         content_type="application/json",
                         headers=self.auth_header,
                         data=self.data2)
        assert json.loads(r.data)["updated_builds_ids"] == [1]
        assert json.loads(r.data)["non_existing_builds_ids"] == []

        updated = self.models.Build.query.filter(
            self.models.Build.id == 1).first()
        assert updated.status == 1
        assert updated.ended_on == 139086644000

    def test_update_more_existent_and_non_existent_builds(
            self, f_users, f_coprs, f_mock_chroots, f_builds, f_db):

        self.b1.started_on = None
        self.db.session.add(self.b1)
        self.db.session.commit()

        r = self.tc.post("/backend/update/",
                         content_type="application/json",
                         headers=self.auth_header,
                         data=self.data3)

        assert sorted(json.loads(r.data)["updated_builds_ids"]) == [1, 2]
        assert sorted(json.loads(r.data)["non_existing_builds_ids"]) == [
            123321, 1234321]

        started = self.models.Build.query.filter(
            self.models.Build.id == 1).first()
        assert started.started_on == 139086644000

        ended = self.models.Build.query.filter(
            self.models.Build.id == 2).first()
        assert ended.status == 0
        assert ended.results == "http://server/results/foo/bar/"
        assert ended.ended_on == 139086644000

    def test_build_ended_emmits_signal(self, f_users, f_coprs, f_builds, f_db):
        # TODO: this should probably be mocked...
        signals_received = []

        def test_receiver(sender, **kwargs):
            signals_received.append(kwargs["build"])
        build_finished.connect(test_receiver)
        self.tc.post("/backend/update/",
                     content_type="application/json",
                     headers=self.auth_header,
                     data=self.data3)
        assert len(signals_received) == 1
        self.db.session.add(self.b2)
        assert signals_received[0].id == 2


class TestWaitingActions(CoprsTestCase):

    def test_no_waiting_actions(self):
        assert '"actions": []' in self.tc.get(
            "/backend/waiting/", headers=self.auth_header).data

    def test_waiting_actions_only_lists_not_started_or_ended(
            self, f_users, f_coprs, f_actions, f_db):

        r = self.tc.get("/backend/waiting/", headers=self.auth_header)
        assert len(json.loads(r.data)["actions"]) == 2


class TestUpdateActions(CoprsTestCase):
    data1 = """
{
  "actions":[
    {
      "id": 1,
      "result": 1,
      "message": "no problem",
      "ended_on": 139086644000
    }
  ]
}"""
    data2 = """
{
  "actions":[
    {
      "id": 1,
      "result": 1,
      "message": null,
      "ended_on": 139086644000
    },
    {
      "id": 2,
      "result": 2,
      "message": "problem!",
      "ended_on": 139086644000
    },
    {
      "id": 100,
      "result": 123,
      "message": "wheeeee!",
      "ended_on": 139086644000
    }
  ]
}"""

    def test_update_one_action(self, f_users, f_coprs, f_actions, f_db):
        r = self.tc.post("/backend/update/",
                         content_type="application/json",
                         headers=self.auth_header,
                         data=self.data1)
        assert json.loads(r.data)["updated_actions_ids"] == [1]
        assert json.loads(r.data)["non_existing_actions_ids"] == []

        updated = self.models.Action.query.filter(
            self.models.Action.id == 1).first()
        assert updated.result == 1
        assert updated.message == "no problem"
        assert updated.ended_on == 139086644000

    def test_update_more_existent_and_non_existent_builds(self, f_users,
                                                          f_coprs, f_actions,
                                                          f_db):
        r = self.tc.post("/backend/update/",
                         content_type="application/json",
                         headers=self.auth_header,
                         data=self.data2)
        assert sorted(json.loads(r.data)["updated_actions_ids"]) == [1, 2]
        assert json.loads(r.data)["non_existing_actions_ids"] == [100]

        updated = self.models.Action.query.filter(
            self.models.Action.id == 1).first()
        assert updated.result == 1
        assert updated.message is None
        assert updated.ended_on == 139086644000

        updated2 = self.models.Action.query.filter(
            self.models.Action.id == 2).first()
        assert updated2.result == 2
        assert updated2.message == "problem!"
        assert updated2.ended_on == 139086644000
