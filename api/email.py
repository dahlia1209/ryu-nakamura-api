from typing import List, Optional,Literal
from models.user import User
from managers.email_manager import EmailManager
from models.email import EmailResponse,EmailRequest,EmailContent,EmailRecipients,EmailMessage,EmailAddress
from models.contact import ContactMessage
import os
import json
import datetime

# 登録完了メール送信関数
def send_registration_email(user_item: User):
    try:
        email_manager = EmailManager()
        
        reply=EmailRequest(
        content=EmailContent.registration(
            email=user_item.email,
            name=user_item.email
            ),
        recipients=EmailRecipients(
            to=[EmailAddress(address=user_item.email,displayName=user_item.email)],
            bcc=[EmailAddress(address=os.getenv('RECIPENTS_ADDRESS'),displayName=os.getenv('RECIPENTS_ADDRESS'))]
            ),
        senderAddress=os.getenv('SENDER_ADDRESS'),
        )
        
        poller = email_manager.client.begin_send(reply.model_dump())
        mail_result = poller.result()
        return mail_result
        
    except Exception as e:
        print(f"登録完了メール送信エラー: {str(e)}")
        
#問い合わせメール送信
def notify_contact_message(message: ContactMessage):
    try:
        email_manager=EmailManager()
        reply=EmailRequest(
                content=EmailContent.contact(
                    contact_name=message.name,
                    contact_message=message.message,
                    contact_subject=message.subject,
                    ),
                recipients=EmailRecipients(
                    to=[EmailAddress(address=message.email,displayName=message.email)],
                    bcc=[EmailAddress(address=os.getenv('RECIPENTS_ADDRESS'),displayName=os.getenv('RECIPENTS_ADDRESS'))]
                    ),
                senderAddress=os.getenv('SENDER_ADDRESS'),
            )
        
        
        poller = email_manager.client.begin_send(reply.model_dump())
        mail_result = poller.result()
        
        return mail_result
        
    except Exception as e:
        print(f"メール送信エラー: {str(e)}")
        
        
#購入完了メール送信
def purchased_complete(customer_name: str,customer_email:str,order_id:str,order_date:datetime.datetime,content_title:str,price:int,content_html:str,payment_method:str="クレジットカード"):
    try:
        email_manager=EmailManager()
        reply=EmailRequest(
            content=EmailContent.purchased_order(
                name=customer_name,
                order_id=order_id,
                order_date=order_date.strftime('%Y年%m月%d日 %H時%M分'),
                content_title=content_title,
                price=str(price),
                payment_method="クレジットカード",
                content_html=content_html,
                ),
            recipients=EmailRecipients(
                to=[EmailAddress(address=customer_email,displayName=customer_email)],
                bcc=[EmailAddress(address=os.getenv('RECIPENTS_ADDRESS'),displayName=os.getenv('RECIPENTS_ADDRESS'))]
                ),
            senderAddress=os.getenv('SENDER_ADDRESS'),
        )
        
        poller = email_manager.client.begin_send(reply.model_dump())
        mail_result = poller.result()
        
        return mail_result
        
    except Exception as e:
        print(f"メール送信エラー: {str(e)}")