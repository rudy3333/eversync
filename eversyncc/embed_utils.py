import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json

def get_oembed_info(url):
    try:
        oembed_endpoints = [
            f"https://www.tiktok.com/oembed?url={url}",
            f"https://www.reddit.com/oembed?url={url}",
            f"https://www.youtube.com/oembed?url={url}&format=json"
        ]
        
        for endpoint in oembed_endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'title': data.get('title', ''),
                        'html': data.get('html', ''),
                        'thumbnail_url': data.get('thumbnail_url', ''),
                        'author_name': data.get('author_name', ''),
                        'provider_name': data.get('provider_name', '')
                    }
            except:
                continue
    except:
        pass
    return None

def get_open_graph_info(url):
    """Get embed information using Open Graph Protocol"""
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        og_tags = {}
        for tag in soup.find_all('meta', property=re.compile(r'^og:')):
            og_tags[tag.get('property', '')[3:]] = tag.get('content', '')
        
        if og_tags:
            html = '<div class="og-embed">'
            
            if 'image' in og_tags:
                html += f'<img src="{og_tags["image"]}" alt="{og_tags.get("title", "")}" style="max-width: 100%; height: auto;">'
            
            if 'description' in og_tags:
                html += f'<p>{og_tags["description"]}</p>'
            
            if 'site_name' in og_tags:
                html += f'<small>via {og_tags["site_name"]}</small>'
            
            html += f'<a href="{url}" target="_blank">View original</a></div>'
            
            return {
                'title': og_tags.get('title', ''),
                'html': html,
                'thumbnail_url': og_tags.get('image', ''),
                'description': og_tags.get('description', ''),
                'site_name': og_tags.get('site_name', '')
            }
    except:
        pass
    return None

def get_youtube_embed(url):
    if 'youtube.com' in url:
        video_id = re.search(r'v=([^&]+)', url)
        if video_id:
            video_id = video_id.group(1)
    elif 'youtu.be' in url:
        video_id = url.split('/')[-1]
    else:
        return None
    
    if video_id:
        return {
            'title': f'YouTube Video',
            'html': f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
        }
    return None

def get_twitter_embed(url):
    """Extract Twitter post ID and return embed HTML"""
    url = url.replace('x.com', 'twitter.com')
    
    tweet_id = re.search(r'twitter\.com/\w+/status/(\d+)', url)
    if tweet_id:
        tweet_id = tweet_id.group(1)
        return {
            'title': 'Twitter Post',
            'html': f'<blockquote class="twitter-tweet"><a href="{url}"></a></blockquote><script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
        }
    return None

def get_webpage_embed(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get title
        title = soup.title.string if soup.title else url
        
        description = ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        
        image = ''
        first_img = soup.find('img')
        if first_img:
            image = first_img.get('src', '')
            if not image.startswith(('http://', 'https://')):
                parsed_url = urlparse(url)
                image = urljoin(f"{parsed_url.scheme}://{parsed_url.netloc}", image)
        
        html = f'<div class="webpage-embed">'
        if image:
            html += f'<img src="{image}" alt="{title}">'
        if description:
            html += f'<p>{description}</p>'
        html += f'<a href="{url}" target="_blank">View original</a></div>'
        
        return {
            'title': title,
            'html': html
        }
    except Exception as e:
        return None

def get_embed_info(url):
    embed_info = get_oembed_info(url)
    if embed_info:
        return embed_info
    
    embed_info = get_open_graph_info(url)
    if embed_info:
        return embed_info
    
    if 'youtube.com' in url or 'youtu.be' in url:
        return get_youtube_embed(url)
    
    if 'twitter.com' in url or 'x.com' in url:
        return get_twitter_embed(url)
    
    return get_webpage_embed(url) 