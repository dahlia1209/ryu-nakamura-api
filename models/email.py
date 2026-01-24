from pydantic import BaseModel,Field
from typing import List, Optional,Dict
from bs4 import BeautifulSoup
import os

class EmailAddress(BaseModel):
    """Email address with optional display name"""
    address: str = Field(..., description="Email address. Required.")
    displayName: Optional[str] = Field(None, description="Optional. Email display name.")


class EmailContent(BaseModel):
    """Email content structure"""
    subject: str = Field(..., description="Subject of the email message. Required.")
    html: Optional[str] = Field(None, description="Optional. Html version of the email message.")
    plainText: Optional[str] = Field(None, description="Optional. Plain text version of the email message.")
    
    
    #メールヘッダー
    @staticmethod
    def get_html_header() :
        return f"""
                <div class="mailer-header" style="padding-top:24px;padding-right:16px;padding-left:16px;margin-bottom:24px;text-align:center;background-color:#fff;">
                    <table style="width:100%;max-width:600px;margin-right:auto;margin-left:auto">
                        <tr>
                            <td style="text-align:center;vertical-align:middle">
                                <a href="https://www.ryu-nakamura.com" style="color:#787c7b;text-decoration:none;">
                                Ryu Nakamura
                                </a>
                            </td>
                        </tr>
                    </table>
                </div>
                """
    
    #メールフッター
    @staticmethod
    def get_html_footer() :
            return f"""
                    <div class="mailer-footer" style="padding-right:16px;padding-left:16px">
                        <table style="width:100%;max-width:600px;margin-right:auto;margin-left:auto">
                            <tr>
                                <td>
                                    <p>このメールは送信専用のメールアドレスから配信されています。ご返信いただいてもお答えできませんのでご了承ください。</p>
                                    <p>------------------------------</p>
                                    <p>屋号：RyuTech</p>
                                    <p>Webサイト：<a href="https://www.ryu-nakamura.com">https://www.ryu-nakamura.com</a></p>
                                    <p>------------------------------</p>
                                    <p class="mailer-footer__menu" style="padding-top:32px;padding-bottom:16px;font-size:14px;line-height:2">
                                    </p>
                                    <p class="mailer-footer__copyright" style="padding-top:16px;padding-bottom:40px;font-size:12px;color:#787c7b;border-top:1px solid #e6e6e6">
                                    <a href="https://www.ryu-nakamura.com/" style="color:#787c7b;text-decoration:none;">© 2025 中村システムエンジニアリング事業所.</a>
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </div>
                    """
    
    #メール本文テンプレ
    @staticmethod
    def get_html_body(main:Optional[str]=None,header:Optional[str]=None,footer:Optional[str]=None):
        if header is None:
            header = EmailContent.get_html_header()
        if footer is None:
            footer = EmailContent.get_html_footer()
                    
        return f"""
        <body style="margin:0;padding:0;font-size:14px;font-family:sans-serif;background-color:#fff;">
            <div class="wrapper" style="margin:0;padding:0;word-break:break-all;background-color:#fff">
            {header}
            {main}
            {footer}
            </div>
        </body>
        """
    
    #購入時のメール本文
    @classmethod
    def purchased_order(
        cls,
        name:str,order_id:str,order_date:str,content_title:str,price:str,payment_method:str,content_html:str
    ):
        def _main_title():
                return f"""
                <div class="title" style="margin-bottom:16px">
                <table style="width:100%">
                    <tr>
                    <td>
                        <div class="title__text" style="font-size:16px">
                        <strong>{name}</strong> 様<br>
                        本サイトをご利用いただき、ありがとうございます。<br>
                        ご購入の詳細は以下のとおりです。
                        </div>
                    </td>
                    </tr>
                </table>
                </div>
                """
            
        def _main_order():
            return f"""
            <div class="card" style="border:1px solid #e6e6e6;background-color:#fff;border-radius:4px">
            <table style="width:100%;margin-left:auto;margin-right:auto">
                <tr>
                <td class="card__body" style="padding:24px">
                    <div class="informationList" style="margin-bottom:0">
                    <div class="informationList__item" style="margin-bottom:16px">
                        <b class="informationList__caption" style="display:block">注文ID</b>
                        {order_id}
                    </div>
                    <div class="informationList__item" style="margin-bottom:16px">
                        <b class="informationList__caption" style="display:block">注文日時</b>
                        {order_date}
                    </div>
                    <div class="informationList__item" style="margin-bottom:16px">
                        <b class="informationList__caption" style="display:block">商品</b>
                        {content_title}
                    </div>
                    <div class="informationList__item" style="margin-bottom:16px">
                        <b class="informationList__caption" style="display:block">支払額</b>
                        {price}円
                    </div>
                    <div class="informationList__item" style="margin-bottom:0">
                        <b class="informationList__caption" style="display:block">決済方法</b>
                        {payment_method}
                    </div>
                    </div>
                </td>
                </tr>
            </table>
            </div>
            """
        
        def _main_content():
            return f"""
            <div class="card" style="border:1px solid #e6e6e6;background-color:#fff;border-radius:4px;margin-top:16px">
            <table style="width:100%;margin-left:auto;margin-right:auto">
                <tr>
                <td class="card__body card__body--article" style="padding:16px;width:100%;max-width:568px;word-break:break-word">
                    {content_html}
                </td>
                </tr>
            </table>
            </div>
            """
        
        def _get_html_main():
            return f"""
                <div class="main" style="padding-left:16px;padding-right:16px">
                    <table style="width:100%;max-width:600px;margin-left:auto;margin-right:auto">
                        <tr>
                            <td>
                            {_main_title()}
                            {_main_order()}
                            {_main_content()}
                            </td>
                        </tr>
                    </table>
                </div>
                
                """
            
        subject='【ryu-nakamura.com】ご購入が完了いたしました'
        html=EmailContent.get_html_body(main=_get_html_main())
        soup = BeautifulSoup(html, 'html.parser')
        plainText=soup.get_text()
        return cls(
            subject=subject,
            html=html,
            plainText=plainText
        )

    #問い合わせ時のメール本文
    @classmethod
    def contact(
        cls,
        contact_name:str,contact_subject:str,contact_message:str
    ):
        def _main_title():
                return f"""
                <div class="title" style="margin-bottom:16px">
                <table style="width:100%">
                    <tr>
                    <td>
                        <div class="title__text" style="font-size:16px">
                        <strong>{contact_name}</strong> 様<br>
                        この度はお問い合わせいただき、誠にありがとうございます。<br>
                        下記の内容でお問い合わせを受け付けました。
                        </div>
                    </td>
                    </tr>
                </table>
                </div>
                """
            
        def _main_contact():
            converted_text = contact_message.replace('\n', '<br>')
            return f"""
            <div class="card" style="border:1px solid #e6e6e6;background-color:#fff;border-radius:4px">
            <table style="width:100%;margin-left:auto;margin-right:auto">
                <tr>
                <td class="card__body" style="padding:24px">
                    <div class="informationList" style="margin-bottom:0">
                    <div class="informationList__item" style="margin-bottom:16px">
                        <b class="informationList__caption" style="display:block">件名</b>
                        {contact_subject}
                    </div>
                    <div class="informationList__item" style="margin-bottom:16px">
                        <b class="informationList__caption" style="display:block">メッセージ</b>
                        {converted_text}
                    </div>
                    </div>
                </td>
                </tr>
            </table>
            </div>
            """
        
        
        def _get_html_main():
            return f"""
                <div class="main" style="padding-left:16px;padding-right:16px">
                    <table style="width:100%;max-width:600px;margin-left:auto;margin-right:auto">
                        <tr>
                            <td>
                            {_main_title()}
                            {_main_contact()}
                            </td>
                        </tr>
                    </table>
                </div>
                
                """
            
        subject='【ryu-nakamura.com】お問い合わせありがとうございます'
        html=EmailContent.get_html_body(main=_get_html_main())
        soup = BeautifulSoup(html, 'html.parser')
        plainText=soup.get_text()
        return cls(
            subject=subject,
            html=html,
            plainText=plainText
        )
        
    #アカウント登録完了時のメール本文
    @classmethod
    def registration(
        cls,
        name:str,email:str,
    ):
        def _main_title():
                return f"""
                <div class="title" style="margin-bottom:16px">
                <table style="width:100%">
                    <tr>
                    <td>
                        <div class="title__text" style="font-size:16px">
                        <strong>{name}</strong> 様<br>
                        この度は本サイトにご登録いただき、誠にありがとうございます。<br>
                        下記の通り会員登録が完了しましたのでお知らせいたします。
                        </div>
                    </td>
                    </tr>
                </table>
                </div>
                """
            
        def _main_content():
            return f"""
            <div class="card" style="border:1px solid #e6e6e6;background-color:#fff;border-radius:4px">
            <table style="width:100%;margin-left:auto;margin-right:auto">
                <tr>
                <td class="card__body" style="padding:24px">
                    <div class="informationList" style="margin-bottom:0">
                    <div class="informationList__item" style="margin-bottom:16px">
                        <b class="informationList__caption" style="display:block">メールアドレス</b>
                        {email}
                    </div>
                    </div>
                </td>
                </tr>
            </table>
            </div>
            """
        
        
        def _get_html_main():
            return f"""
                <div class="main" style="padding-left:16px;padding-right:16px">
                    <table style="width:100%;max-width:600px;margin-left:auto;margin-right:auto">
                        <tr>
                            <td>
                            {_main_title()}
                            {_main_content()}
                            </td>
                        </tr>
                    </table>
                </div>
                
                """
            
        subject='【ryu-nakamura.com】アカウント登録完了のお知らせ'
        html=EmailContent.get_html_body(main=_get_html_main())
        soup = BeautifulSoup(html, 'html.parser')
        plainText=soup.get_text()
        return cls(
            subject=subject,
            html=html,
            plainText=plainText
        )


class EmailRecipients(BaseModel):
    """Email recipients structure"""
    to: List[EmailAddress] = Field(default_factory=list, description="To recipients")
    bcc: List[EmailAddress] = Field(default_factory=list, description="BCC recipients")
    cc: List[EmailAddress] = Field(default_factory=list, description="CC recipients")

class EmailAttachment(BaseModel):
    """Email attachment structure"""
    contentInBase64: str = Field(..., description="Base64 encoded contents of the attachment. Required.")
    contentType: str = Field(..., description="MIME type of the content being attached. Required.")
    name: str = Field(..., description="Name of the attachment. Required.")


class EmailRequest(BaseModel):
    """Complete email request structure"""
    content: EmailContent = Field(..., description="Email content")
    recipients: EmailRecipients = Field(..., description="Email recipients")
    senderAddress: str = Field(..., description="Sender email address from a verified domain. Required.")
    attachments: List[EmailAttachment] = Field(default_factory=list, description="Email attachments")
    userEngagementTrackingDisabled: Optional[bool] = Field(
        None, 
        description="Optional. Indicates whether user engagement tracking should be disabled for this request if the resource-level user engagement tracking setting was already enabled in the control plane."
    )
    headers: Optional[Dict[str, str]] = Field(None, description="Optional. Custom email headers to be passed.")
    replyTo: List[EmailAddress] = Field(default_factory=list, description="Reply-to addresses")
    

class EmailMessage(BaseModel):
    senderAddress: str
    recipients: EmailRecipients
    content: EmailContent
    senderName: Optional[str]

class EmailResponse(BaseModel):
    id: str
    status: str
    error: Optional[None] = None
    