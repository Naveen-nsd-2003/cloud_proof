"""
Email notification service using AWS SES
Sends professional HTML emails for invoice and gig notifications
"""

import boto3
from botocore.exceptions import ClientError
import os
from datetime import datetime

# Initialize SES client
ses_client = boto3.client(
    'ses',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Sender email - MUST be verified in AWS SES
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'noreply@cloudcred.com')
SENDER_NAME = 'CloudCred Platform'

def send_invoice_created_email(client_email, client_name, freelancer_name, invoice_data):
    """
    Send email to client when a new invoice is created
    
    Args:
        client_email: Client's email address
        client_name: Client's name
        freelancer_name: Freelancer's name
        invoice_data: Dict with invoice_id, amount, description, created_at
    """
    subject = f"New Invoice from {freelancer_name} - ${invoice_data['amount']}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
            .invoice-box {{ background: white; padding: 20px; border-radius: 8px; 
                           margin: 20px 0; border-left: 4px solid #667eea; }}
            .amount {{ font-size: 32px; font-weight: bold; color: #059669; margin: 10px 0; }}
            .button {{ display: inline-block; background: #16a34a; color: white; 
                      padding: 12px 30px; text-decoration: none; border-radius: 6px; 
                      margin: 20px 0; font-weight: bold; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💼 New Invoice Received</h1>
            </div>
            <div class="content">
                <p>Hi {client_name},</p>
                <p>You have received a new invoice from <strong>{freelancer_name}</strong>.</p>
                
                <div class="invoice-box">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">Invoice Amount</p>
                    <div class="amount">${invoice_data['amount']}</div>
                    <p style="margin: 10px 0 5px 0;"><strong>Description:</strong></p>
                    <p style="margin: 0; color: #4b5563;">{invoice_data['description']}</p>
                    <p style="margin: 15px 0 0 0; font-size: 12px; color: #9ca3af;">
                        Invoice ID: #{invoice_data['invoice_id'][-6:]}<br>
                        Created: {invoice_data['created_at']}
                    </p>
                </div>
                
                <p>Please review and approve this invoice in your CloudCred dashboard. 
                   Once approved, payment will be recorded on the blockchain for transparency.</p>
                
                <a href="https://cloudcred.com/invoice-manager" class="button">
                    View & Approve Invoice
                </a>
                
                <p style="margin-top: 30px; font-size: 14px; color: #6b7280;">
                    <strong>What happens next?</strong><br>
                    1. Review the invoice details<br>
                    2. Click "Approve & Pay" to process payment<br>
                    3. Transaction will be recorded on blockchain<br>
                    4. Freelancer will be notified automatically
                </p>
            </div>
            <div class="footer">
                <p>© 2025 CloudCred - Blockchain-Verified Freelance Platform</p>
                <p>This is an automated notification. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    New Invoice Received
    
    Hi {client_name},
    
    You have received a new invoice from {freelancer_name}.
    
    Amount: ${invoice_data['amount']}
    Description: {invoice_data['description']}
    Invoice ID: #{invoice_data['invoice_id'][-6:]}
    Created: {invoice_data['created_at']}
    
    Please log in to your CloudCred dashboard to review and approve this invoice.
    
    Best regards,
    CloudCred Team
    """
    
    return send_email(client_email, subject, html_body, text_body)


def send_invoice_approved_email(freelancer_email, freelancer_name, client_name, invoice_data):
    """
    Send email to freelancer when invoice is approved
    
    Args:
        freelancer_email: Freelancer's email address
        freelancer_name: Freelancer's name
        client_name: Client's name
        invoice_data: Dict with invoice_id, amount, transaction_hash, pdf_url
    """
    subject = f"🎉 Invoice Approved - ${invoice_data['amount']} Payment Confirmed"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                       color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
            .success-box {{ background: white; padding: 20px; border-radius: 8px; 
                           margin: 20px 0; border-left: 4px solid #10b981; }}
            .amount {{ font-size: 32px; font-weight: bold; color: #059669; margin: 10px 0; }}
            .button {{ display: inline-block; background: #2563eb; color: white; 
                      padding: 12px 30px; text-decoration: none; border-radius: 6px; 
                      margin: 20px 0; font-weight: bold; }}
            .blockchain-badge {{ background: #dbeafe; color: #1e40af; padding: 8px 16px; 
                                border-radius: 20px; font-size: 12px; display: inline-block; 
                                margin: 10px 0; font-family: monospace; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ Payment Approved!</h1>
            </div>
            <div class="content">
                <p>Hi {freelancer_name},</p>
                <p>Great news! <strong>{client_name}</strong> has approved your invoice and the payment has been processed.</p>
                
                <div class="success-box">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">Payment Amount</p>
                    <div class="amount">${invoice_data['amount']}</div>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #9ca3af;">
                        Invoice ID: #{invoice_data['invoice_id'][-6:]}
                    </p>
                    
                    {f'''
                    <div class="blockchain-badge">
                        🔗 Blockchain Verified: {invoice_data.get('transaction_hash', '')[:10]}...
                    </div>
                    ''' if invoice_data.get('transaction_hash') else ''}
                </div>
                
                <p>Your payment has been recorded on the blockchain for transparency and security. 
                   You can download your official receipt below.</p>
                
                {f'''
                <a href="{invoice_data.get('pdf_url')}" class="button">
                    📄 Download Receipt (PDF)
                </a>
                ''' if invoice_data.get('pdf_url') else ''}
                
                <p style="margin-top: 30px; font-size: 14px; color: #6b7280;">
                    <strong>Transaction Details:</strong><br>
                    ✅ Payment approved and verified<br>
                    🔗 Recorded on blockchain<br>
                    📄 Official receipt generated<br>
                    💰 Funds processing complete
                </p>
            </div>
            <div class="footer">
                <p>© 2025 CloudCred - Blockchain-Verified Freelance Platform</p>
                <p>This is an automated notification. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    Payment Approved!
    
    Hi {freelancer_name},
    
    Great news! {client_name} has approved your invoice.
    
    Amount: ${invoice_data['amount']}
    Invoice ID: #{invoice_data['invoice_id'][-6:]}
    Transaction Hash: {invoice_data.get('transaction_hash', 'Processing...')}
    
    Your payment has been verified on the blockchain.
    {f"Download receipt: {invoice_data.get('pdf_url')}" if invoice_data.get('pdf_url') else ''}
    
    Best regards,
    CloudCred Team
    """
    
    return send_email(freelancer_email, subject, html_body, text_body)


def send_gig_created_notification(user_email, user_name, gig_data):
    """
    Send email when a new gig is posted (optional feature)
    
    Args:
        user_email: Recipient's email
        user_name: Recipient's name
        gig_data: Dict with title, description, price, freelancer_name, category
    """
    subject = f"New Gig Posted: {gig_data['title']}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
            .gig-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .price {{ font-size: 24px; font-weight: bold; color: #059669; }}
            .button {{ display: inline-block; background: #2563eb; color: white; 
                      padding: 12px 30px; text-decoration: none; border-radius: 6px; 
                      margin: 20px 0; font-weight: bold; }}
            .category-badge {{ background: #dbeafe; color: #1e40af; padding: 4px 12px; 
                              border-radius: 12px; font-size: 12px; display: inline-block; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 New Gig Available</h1>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>
                <p>A new gig has been posted on CloudCred that might interest you!</p>
                
                <div class="gig-box">
                    <h2 style="margin: 0 0 10px 0; color: #1f2937;">{gig_data['title']}</h2>
                    {f'<span class="category-badge">{gig_data.get("category")}</span>' if gig_data.get('category') else ''}
                    <p style="color: #4b5563; margin: 15px 0;">{gig_data['description'][:200]}...</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
                        <span class="price">${gig_data['price']}</span>
                        <span style="color: #6b7280; font-size: 14px;">by {gig_data['freelancer_name']}</span>
                    </div>
                </div>
                
                <a href="https://cloudcred.com/browse-gigs" class="button">
                    Browse All Gigs
                </a>
            </div>
            <div class="footer">
                <p>© 2025 CloudCred - Blockchain-Verified Freelance Platform</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    New Gig Posted
    
    Hi {user_name},
    
    A new gig is available on CloudCred:
    
    {gig_data['title']}
    Price: ${gig_data['price']}
    By: {gig_data['freelancer_name']}
    
    {gig_data['description'][:200]}...
    
    Visit CloudCred to browse all available gigs.
    
    Best regards,
    CloudCred Team
    """
    
    return send_email(user_email, subject, html_body, text_body)


def send_email(recipient_email, subject, html_body, text_body):
    """
    Core function to send email via AWS SES
    
    Args:
        recipient_email: Email address to send to
        subject: Email subject line
        html_body: HTML version of email
        text_body: Plain text version of email
    
    Returns:
        dict: {'success': bool, 'message_id': str} or {'success': False, 'error': str}
    """
    try:
        response = ses_client.send_email(
            Source=f'{SENDER_NAME} <{SENDER_EMAIL}>',
            Destination={
                'ToAddresses': [recipient_email]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    },
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        message_id = response['MessageId']
        print(f"✅ Email sent successfully to {recipient_email} | Message ID: {message_id}")
        
        return {
            'success': True,
            'message_id': message_id
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"❌ Email sending failed: {error_code} - {error_message}")
        
        return {
            'success': False,
            'error': f"{error_code}: {error_message}"
        }
    except Exception as e:
        print(f"❌ Unexpected email error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def format_datetime(dt_string):
    """Helper to format datetime strings for emails"""
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime('%B %d, %Y at %I:%M %p')
    except:
        return dt_string