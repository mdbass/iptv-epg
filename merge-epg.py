import requests
import gzip
import json
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime

def download_file(url):
    """Download file from URL"""
    print(f"Downloading: {url}")
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    return response.content

def decompress_gz(data):
    """Decompress .gz file"""
    print("Decompressing .gz file...")
    with gzip.GzipFile(fileobj=BytesIO(data)) as f:
        return f.read()

def parse_xml(xml_data):
    """Parse XML data"""
    return ET.fromstring(xml_data)

def filter_channels(root, channel_ids, prefix):
    """Filter channels and add prefix to IDs"""
    print(f"Filtering channels with prefix: {prefix}")
    
    # Create new root element
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'EPG Merger')
    new_root.set('generator-info-url', 'https://github.com/mdbass/iptv-epg')
    
    # Check if we want all channels
    load_all = (channel_ids == "*")
    
    if load_all:
        print("Loading ALL channels from this source")
        channel_ids_str = None
    else:
        # Convert channel_ids to strings for comparison
        channel_ids_str = [str(cid) for cid in channel_ids]
    
    # Filter and add channels
    channels_found = []
    for channel in root.findall('channel'):
        channel_id = channel.get('id')
        
        # Include channel if loading all OR if in the channel list
        if load_all or channel_id in channel_ids_str:
            # Create new channel element with prefixed ID
            new_channel = ET.Element('channel')
            new_channel.set('id', f"{prefix}{channel_id}")
            
            # Copy all child elements
            for child in channel:
                new_channel.append(child)
            
            new_root.append(new_channel)
            channels_found.append(channel_id)
    
    if load_all:
        print(f"Loaded {len(channels_found)} channels (all available)")
    else:
        print(f"Found {len(channels_found)} channels: {channels_found}")
    
    # Filter and add programmes
    programmes_count = 0
    for programme in root.findall('programme'):
        channel_id = programme.get('channel')
        
        # Include programme if loading all OR if channel is in the list
        if load_all or channel_id in channel_ids_str:
            # Create new programme element with prefixed channel ID
            new_programme = ET.Element('programme')
            new_programme.set('channel', f"{prefix}{channel_id}")
            new_programme.set('start', programme.get('start'))
            new_programme.set('stop', programme.get('stop'))
            
            # Copy all attributes except channel, start, stop (already set)
            for attr, value in programme.attrib.items():
                if attr not in ['channel', 'start', 'stop']:
                    new_programme.set(attr, value)
            
            # Copy all child elements
            for child in programme:
                new_programme.append(child)
            
            new_root.append(new_programme)
            programmes_count += 1
    
    print(f"Added {programmes_count} programmes")
    return new_root

def merge_epg_sources(sources_config):
    """Process all EPG sources and merge them"""
    print("=" * 50)
    print("Starting EPG Merger")
    print(f"Time: {datetime.utcnow().isoformat()}")
    print("=" * 50)
    
    # Create main root element
    merged_root = ET.Element('tv')
    merged_root.set('generator-info-name', 'EPG Merger')
    merged_root.set('generator-info-url', 'https://github.com/mdbass/iptv-epg')
    
    total_channels = 0
    total_programmes = 0
    
    for idx, source in enumerate(sources_config['sources'], 1):
        print(f"\n--- Processing Source {idx}/{len(sources_config['sources'])} ---")
        print(f"Name: {source['name']}")
        print(f"URL: {source['url']}")
        
        try:
            # Download file
            data = download_file(source['url'])
            
            # Decompress if .gz
            if source['format'].lower() == 'gz':
                data = decompress_gz(data)
            
            # Parse XML
            root = parse_xml(data)
            
            # Filter channels and add prefix
            filtered_root = filter_channels(root, source['channels'], source['prefix'])
            
            # Merge into main root
            channels = filtered_root.findall('channel')
            programmes = filtered_root.findall('programme')
            
            for channel in channels:
                merged_root.append(channel)
                total_channels += 1
            
            for programme in programmes:
                merged_root.append(programme)
                total_programmes += 1
            
            print(f"✓ Source {idx} completed successfully")
            
        except Exception as e:
            print(f"✗ Error processing source {idx}: {str(e)}")
            continue
    
    print("\n" + "=" * 50)
    print("EPG Merge Complete")
    print(f"Total Channels: {total_channels}")
    print(f"Total Programmes: {total_programmes}")
    print("=" * 50)
    
    return merged_root

def save_xml(root, output_path):
    """Save XML to file with proper formatting"""
    print(f"\nSaving to: {output_path}")
    
    # Create XML string with declaration
    xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_string += ET.tostring(root, encoding='unicode')
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    
    print("✓ File saved successfully")

def main():
    # Load configuration
    print("Loading configuration...")
    with open('sources.json', 'r') as f:
        config = json.load(f)
    
    # Process and merge EPG sources
    merged_root = merge_epg_sources(config)
    
    # Save output
    save_xml(merged_root, 'output/guide.xml')
    
    print("\n✓ All done!")

if __name__ == "__main__":
    main()