import praw
from datetime import datetime, timedelta
import json
from collections import defaultdict
import os
from dotenv import load_dotenv

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Load environment variables
load_dotenv()

class SimpleRedditMonitor:
    def __init__(self):
        """Initialize with environment variables for security"""
                
                # Reddit configuration from env (read-only access)
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'WeeklyReportBot/1.0'),
            username=None,  # No username for read-only
            password=None   # No password for read-only
        )
        
        # ADD DEBUG CODE:
        print(f"🔍 Debug - Client ID length: {len(os.getenv('REDDIT_CLIENT_ID', ''))}")
        print(f"🔍 Debug - Client Secret length: {len(os.getenv('REDDIT_CLIENT_SECRET', ''))}")
        print(f"🔍 Debug - User Agent: {os.getenv('REDDIT_USER_AGENT', 'NOT SET')}")
        
        # Test Reddit connection
        try:
            print(f"🔍 Debug - Testing Reddit connection...")
            test_user = self.reddit.user.me()
            print(f"🔍 Debug - Reddit connection successful! User: {test_user}")
        except Exception as e:
            print(f"🔍 Debug - Reddit connection failed: {e}")
                

        
    
        
        # Fitness/nutrition keywords to monitor
        self.keywords = [
            'pre-workout', 'preworkout', 'pre workout',
            'hydration', 'dehydration', 'dehydrated',
            'electrolyte', 'electrolytes', 'sodium', 'potassium',
            'lactic acid buffer', 'lactate buffer', 'buffering',
            'creatine', 'beta alanine', 'citrulline',
            'energy drink', 'caffeine', 'stimulant',
            'bcaa', 'amino acids', 'protein powder',
            'recovery drink', 'post workout',
            'muscle cramps', 'fatigue', 'endurance', 'beetroot', 'cordyceps',
        ]
        
        # Specific competitors to track
        self.competitor_brands = [
            'puresport', 'pure sport',
            'marchon', 'marchon',
            'xendurance', 'x-endurance', 'xendurance',
            'esn', 'esn supplements',
            'myprotein', 'my protein',
            'cadence', 'cadence nutrition', 'gold standard'
        ]
        
        # Relevant fitness subreddits (smaller list for testing)
        self.subreddits = ['fitness']
    
    def validate_config(self):
        """Validate that all required environment variables are set"""
        required_vars = [
            'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        print("✅ All required environment variables are set")
        return True

    def search_reddit_posts(self, days_back=7, limit_per_subreddit=50):
        """Search Reddit for posts using direct JSON API (no auth required)"""
        import requests
        import time
        
        all_posts = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        print(f"Searching {len(self.subreddits)} subreddits for posts from the last {days_back} days...")
        
        for subreddit_name in self.subreddits:
            try:
                # Use Reddit's public JSON API
                url = f"https://www.reddit.com/r/{subreddit_name}/new.json?limit={limit_per_subreddit}"
                headers = {'User-Agent': os.getenv('REDDIT_USER_AGENT', 'WeeklyReportBot/1.0')}
                
                print(f"🔍 Debug - Fetching from: {url}")
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    print(f"  r/{subreddit_name}: Error - HTTP {response.status_code}")
                    continue
                    
                data = response.json()
                posts_found = 0
                
                # Parse the JSON response
                for post in data['data']['children']:
                    post_data = post['data']
                    post_date = datetime.fromtimestamp(post_data['created_utc'])
                    
                    if post_date < cutoff_date:
                        continue
                    
                    # Check if any keywords or competitor brands match
                    text_to_search = f"{post_data['title']} {post_data.get('selftext', '')}".lower()
                    matched_keywords = [kw for kw in self.keywords if kw.lower() in text_to_search]
                    matched_competitors = [comp for comp in self.competitor_brands if comp.lower() in text_to_search]
                    
                    if matched_keywords or matched_competitors:
                        post_info = {
                            'title': post_data['title'],
                            'score': post_data['score'],
                            'num_comments': post_data['num_comments'],
                            'subreddit': subreddit_name,
                            'matched_keywords': matched_keywords,
                            'matched_competitors': matched_competitors,
                            'permalink': f"https://reddit.com{post_data['permalink']}"
                        }
                        all_posts.append(post_info)
                        posts_found += 1
                
                print(f"  r/{subreddit_name}: {posts_found} relevant posts")
                time.sleep(1)  # Be nice to Reddit's servers
                        
            except Exception as e:
                print(f"  r/{subreddit_name}: Error - {e}")
                continue
        
        print(f"\n📊 Total posts found: {len(all_posts)}")
        return all_posts
    
    def generate_simple_report(self, posts):
        """Generate a simple HTML report"""
        report_date = datetime.now().strftime("%Y-%m-%d")
        
        # Count mentions
        keyword_counts = defaultdict(int)
        competitor_counts = defaultdict(int)
        
        for post in posts:
            for keyword in post['matched_keywords']:
                keyword_counts[keyword] += 1
            for competitor in post['matched_competitors']:
                competitor_counts[competitor.title()] += 1
        
        # Create HTML report
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reddit Fitness Monitor - {report_date}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f6fa; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                h1 {{ color: #2c3e50; text-align: center; }}
                .section {{ background: white; margin: 20px 0; padding: 20px; border-radius: 10px; }}
                .post {{ border-left: 4px solid #3498db; padding: 10px; margin: 10px 0; background: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏋️ Reddit Fitness Monitor Report</h1>
                <div class="section">
                    <h2>📊 Summary</h2>
                    <p><strong>Report Date:</strong> {report_date}</p>
                    <p><strong>Posts Found:</strong> {len(posts)}</p>
                    <p><strong>Subreddits Monitored:</strong> {', '.join(self.subreddits)}</p>
                </div>
                
                <div class="section">
                    <h2>🎯 Target Competitor Mentions</h2>
        """
        
        if competitor_counts:
            for comp, count in sorted(competitor_counts.items(), key=lambda x: x[1], reverse=True):
                html += f"<p><strong>{comp}:</strong> {count} mentions</p>"
        else:
            html += "<p>No competitor mentions found this week.</p>"
        
        html += """
                </div>
                
                <div class="section">
                    <h2>📝 Top Keywords</h2>
        """
        
        for keyword, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            html += f"<p><strong>{keyword}:</strong> {count} mentions</p>"
        
        html += """
                </div>
                
                <div class="section">
                    <h2>🔥 Sample Posts</h2>
        """
        
        # Show top posts by engagement
        top_posts = sorted(posts, key=lambda x: x['score'] + x['num_comments'], reverse=True)[:10]
        
        for post in top_posts:
            matches = ', '.join(post['matched_keywords'] + post['matched_competitors'])
            html += f"""
                <div class="post">
                    <h4><a href="{post['permalink']}" target="_blank">{post['title']}</a></h4>
                    <p>r/{post['subreddit']} | ⬆️ {post['score']} | 💬 {post['num_comments']}</p>
                    <p><strong>Matches:</strong> {matches}</p>
                </div>
            """
        
        html += f"""
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

    def save_report_locally(self, html_report):
        """Save the report to a local HTML file"""
        filename = f"reddit_fitness_report_{datetime.now().strftime('%Y-%m-%d')}.html"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"✅ Report saved as: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error saving report: {e}")
            return None
    
    def send_email_report(self, html_report, subject=None):
        """Send the HTML report via email"""
        
        # Email configuration from environment variables
        email_from = os.getenv('EMAIL_FROM')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_to = os.getenv('EMAIL_TO')
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.office365.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        
        if not all([email_from, email_password, email_to]):
            print("⚠️  Email credentials not configured, skipping email")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject or f"Reddit Fitness Report - {datetime.now().strftime('%Y-%m-%d')}"
            msg['From'] = email_from
            msg['To'] = email_to
            
            # Add HTML content
            html_part = MIMEText(html_report, 'html')
            msg.attach(html_part)
            
            # Send email
            print(f"📧 Sending email report to {email_to}...")
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Enable encryption
                server.login(email_from, email_password)
                server.send_message(msg)
            
            print("✅ Email sent successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
    
    def run_report(self):
        """Execute the report process"""
        print(f"\n🚀 Starting Simple Reddit Monitor at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        try:
            # Validate configuration
            self.validate_config()
            
            # Search Reddit
            posts = self.search_reddit_posts(days_back=7)
            if not posts:
                print("⚠️  No relevant posts found this week")
                # Still generate and send empty report
                html_report = self.generate_simple_report([])
                self.save_report_locally(html_report)
                self.send_email_report(html_report, "Reddit Fitness Report - No Posts Found")
                return
            
            # Generate Report
            print("\n📄 Generating report...")
            html_report = self.generate_simple_report(posts)
            
            # Save Report Locally
            self.save_report_locally(html_report)
            
            # Send Email Report
            self.send_email_report(html_report)
            
            print(f"\n🎉 Report completed successfully!")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error during report generation: {e}")
            raise

def main():
    """Main function"""
    monitor = SimpleRedditMonitor()
    monitor.run_report()


if __name__ == "__main__":
    main()
