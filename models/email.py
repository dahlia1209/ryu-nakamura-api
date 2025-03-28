from pydantic import BaseModel
from typing import List, Optional


class EmailAddress(BaseModel):
    address: str

class EmailRecipients(BaseModel):
    to: List[EmailAddress]
    
    def getFirst(self):
        if self.to is not None:
            return self.to[0].address
        else:
            return None

class EmailContent(BaseModel):
    subject: str
    plainText: str
    html: Optional[str] = None


class EmailMessage(BaseModel):
    senderAddress: str
    recipients: EmailRecipients
    content: EmailContent
    senderName: Optional[str]


class EmailResponse(BaseModel):
    id: str
    status: str
    error: Optional[None] = None
    