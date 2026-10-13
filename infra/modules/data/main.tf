locals {
  tables = { customers = "customer_id", accounts = "account_id", transfers = "transfer_id" }
}

resource "aws_dynamodb_table" "this" {
  for_each     = local.tables
  name         = "${var.name}-${each.key}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = each.value
  attribute {
    name = each.value
    type = "S"
  }
  server_side_encryption {
    enabled = true
  }
  point_in_time_recovery {
    enabled = true
  }
}
