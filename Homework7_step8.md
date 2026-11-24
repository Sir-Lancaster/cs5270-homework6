# Step 8 Answers
1. Why is it possible that Update and Delete Widget Requests may fail, even when you were running just one Consumer?

One of the most common reasons I saw in the logs is that the delete or update request were processed by the consumer before processing the create request, causing it to log a warning and move on. One reason for this is that SQS, s3, and DynamoDB don't have first in first out architectures, and so there's no guarantee that the create request will be picked up by the consumer before the update or delete requests. 

2. How would this possible behavior impact the design of distributed applications that use queues?

One impact is what's seen in my implementation, it's designed to simply log a warning and move on. Another would be to keep the request in memory, and while the list of request id's is not empty, check new requests for the create request --> create ---> process old request in memory --> remove the item from local list. 