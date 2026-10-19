# Data module

Three on-demand DynamoDB tables use string partition keys, encryption with the AWS-managed DynamoDB key, and point-in-time recovery. There are no public customer datasets or real records. The app atomically changes accounts and inserts transfers. Initial synthetic fixtures are loaded by an authenticated administrator; the app cannot seed customers or arbitrarily put accounts. No deletion protection is set so the operator can destroy this disposable lab; backup/retention decisions belong to the exercise owner.
