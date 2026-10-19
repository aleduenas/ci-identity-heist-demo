output "audit_bucket_name" {
  value = aws_s3_bucket.audit.id
}
output "trail_arn" {
  value = aws_cloudtrail.this.arn
}
