from unittest import TestCase
import json
import copy
from signingscript.task import validate_signature, \
    TaskVerificationError
from jsonschema.exceptions import ValidationError
from jose.exceptions import ExpiredSignatureError, JWSError
from . import PUB_KEY

valid_task = json.loads("""
{
  "provisionerId": "meh",
  "workerType": "workertype",
  "schedulerId": "task-graph-scheduler",
  "taskGroupId": "some",
  "routes": [],
  "retries": 5,
  "created": "2015-05-08T16:15:58.903Z",
  "deadline": "2015-05-08T18:15:59.010Z",
  "expires": "2016-05-08T18:15:59.010Z",
  "scopes": ["signing"],
  "payload": {
    "signingManifest": "manifest.json"
  },
  "extra": {
    "signing": {
      "signature": "blah"
    }
  }
}
""")

valid_signature = """eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE0NDYyMzEx
MjYsInZlcnNpb24iOiIxIiwiZXhwIjoxNzYxNTkxMTI2LCJ0YXNrSWQiOiJibGFoIn0.n8PSQNIWNw
YmGrUsV_Fx_ihW0qZDTzl_UnPULUautkdu60A1tHJi4xTC6yDodzlnyiTDz89XPSxl69yeONsNxceq
BKO3D4WNKqbr8yHb4-l4GL7JHqvsjoxcow07SymQX3uDiBBb196VWVH4MhoMspW0wbhpQLXPuSL3KB
X4N1feLk-KzG_x2YOu4v7b13SR0U8PlNAY4-w_jbnLr1uSsAIouCPKoE7GdG6St3y7e6fE_2wqUpMJ
jP5RhnbbjH0LnVM1KR9So7QXDO7Uu_qsDDktxZiuU37gw9fp6KspuQI7rSX1imGHptjOzW7PPVw6K9
T7hhZEPIevRfSMeh5SYg""".replace("\n", "")
invalid_signature = """eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE0NDYyMj
k5MjUsInZlcnNpb24iOiIxIiwiZXhwIjoxNzYxNTg5OTI1LCJ0YXNrSWQiOiJibGFoIn0.W7TKWg01
AYfzN9teihmnlxHY5vJZPvODL6TFY8sStceoPNdosjxovI0FuqE-O1BXn58nO5RRVQGY5lr0QSlmud
8_utdA4mJokOazkQYhfGAwoX1G-AtMMtvc0uiCnmu0dkvwD5zCrX3gnADvtIZU-oEiJ0rpvhUlqdTO
ufDCcph2fkOSF_zrLBcm5RdN6wMfvEHplT3swgP9SganNX_ui982EqvPvkDYL-rleGhkdUX3vaO_1r
ycl28W-44u-631tb7yenFkucX9aBzI21KtlfwWfRL0e9ZR3oWnUW5xcVTzHEQxeXBiAbHNddZiaZju
swAhidx7gxsxMllsH0tL4Q""".replace("\n", "")
expired_task = """eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE0NDYyMjk5NDU
sInZlcnNpb24iOiIxIiwiZXhwIjoxNDQ2MjI5OTQ1LCJ0YXNrSWQiOiJibGFoIn0.AaTv5YZ0RdJz8
52erq28AbHLB3w_Xg4G0eRpZRNbmIRYZWhBISugKSr-_sn5jSb-NCj4GtNWkki4F2Sy04mOmDMJVU2
FSKgLoOcQ1yvi6s1ZZgvlb4ZCM_xBdqO9vFpp79Z9F7WirvU7x7GIB15SsYWt9EcR7MIjq1XakDx-n
x2H4UxWRMnziEbOFQTmqwKkEZVcdPrBlr7bL-xlIOptkyftyKGgtOnpwXnYWUtr2OxdCetxQil3mX9
81JHu66HQ2_wYOoeo5NhTaWhu_rqMZhLyNN-IWQxwtJyzeQHheNTAtt406cHAog5W3GfDCSha6Kjsk
KHPilsSodPAQNpiQQ""".replace("\n", "")
no_task_id_signature = """eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE0NDY
yMjk5NjgsInRhc2siOiJibGFoIiwidmVyc2lvbiI6IjEiLCJleHAiOjE3NjE1ODk5Njh9.maHJCUgs
PN_2yjKAa24MRriGsZOn98o5oyJKvLzl-xZCI7Fk5IMRgbi4S3-VIWES0KEqnfpf1aUdUD-FGvCbiz
0PQjdChpSD5zrZV84TZDdZ8mbNVvGzGZsX84p0uEZO5CLTcqbQ7lIoMANxUrU1HOxGfwcRixL07DDf
ocl-cmBmx_N6rEl8OSSWPXs-wNXYzta5p7b6fTGNdtEWvoEKW7Vq0BJ6A6LPWmIgO4fzpfVzl2ZeUE
JcXeo3-yuYheGUV3Gy_CV11RZTkS_C-Bf6SAIGuDQ77GHdqAV_mimFUo9d7S7VKfKQZIhBJQmgTQui
Wz9ADBHzXrr_00Uaw9QEvw""".replace("\n", "")

no_scopes = copy.deepcopy(valid_task)
no_scopes["scopes"] = []


class TestValidateTask(TestCase):
    pass
#    def test_valid_task(self):
#        self.assertIsNone(validate_task(valid_task))
#
#    def test_no_scopes(self):
#        self.assertRaises(ValidationError, validate_task, no_scopes)
#
#    def test_signature(self):
#        self.assertRaises(TaskVerificationError, validate_signature, "blah",
#                          no_task_id_signature, PUB_KEY)
#
#    def test_expired_signature(self):
#        self.assertRaises(ExpiredSignatureError, validate_signature, "blah",
#                          expired_task, PUB_KEY)
#
#    def test_invalid_signature(self):
#        self.assertRaises(JWSError, validate_signature, "blah",
#                          invalid_signature, PUB_KEY)
#
#    def test_valid_signature(self):
#        validate_signature("blah", valid_signature, PUB_KEY)
