import requests
from requests.auth import HTTPBasicAuth
import datetime
import urllib3
import os
import shutil
from os import path
from PIL import Image, ImageDraw, ImageFont#, ImageOps
from paramiko import SSHClient
import subprocess
import paramiko

import device_credentials

# disables SSL insecurerequestwarning
import warnings
warnings.filterwarnings("ignore")

# Disable invalid certificate warnings. -> fehler kommt trotzdem
urllib3.disable_warnings()

#output files
map_folder = '/PATH/TO/YOUR/FOLDER/cc-map-exporter/cc_maps'


# authentication
hostname = device_credentials.cc['hostname']
username = device_credentials.cc['user']
password = device_credentials.cc['password']
cc_base_url = 'https://' + hostname

cc_url = cc_base_url + '/dna/system/api/v1/auth/token'
print(cc_url)
response = requests.post(cc_url, verify=False, auth=HTTPBasicAuth(username, password), headers={"Content-Type": "application/json"})
print(response)
token = response.json().get("Token")
if token:
    print("Token saved!")
else:
    print("Failed to authenticate")

cc_headers = {
    "Content-Type": "application/json",
    "X-Auth-Token": token
}


# parameters
default_font = ImageFont.load_default()
ubuntu_font = ImageFont.truetype('/PATH/TO/YOUR/FOLDER/cc-map-exporter/Ubuntu-R.ttf', size=15)


def get_floorIDs_from_cc():
    cc_url = cc_base_url + '/dna/intent/api/v2/site'
    sites = requests.get(cc_url, verify=False, headers=cc_headers).json()

    floorIDs = []
    for site in sites['response']:
        try:
            if site['additionalInfo'][0]['attributes']['type'] == 'floor':
                floorIDs.append(site['id'])
        except Exception as e:
            print('WARN: kein Element "type" vorhanden')

    return floorIDs

def get_floor_details(floor_id):
    cc_url = cc_base_url + '/api/v1/dna-maps-service/domains/' + str(floor_id)
    floor_details = requests.get(cc_url, verify=False, headers=cc_headers).json()
    return floor_details

def get_map_image(image_id):
    cc_url = cc_base_url + '/api/v1' + str(image_id)
    map_image = requests.get(cc_url, verify=False, stream = True, headers=cc_headers).raw
    return map_image

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_accesspoints_position(floor_id):
    cc_url = cc_base_url + '/api/v1/dna-maps-service/domains/' + floor_id + '/aps?pageSize=9999'

    accesspoints = requests.get(cc_url, verify=False, headers=cc_headers).json()

    accesspoints_position = []
    
    try:
        for accesspoint in accesspoints['items']:
            try:
                accesspoint_position = {'name':accesspoint['attributes']['name'], 'xcoordinate':accesspoint['position']['x'], 'ycoordinate':accesspoint['position']['y'], 'ap_type':accesspoint['attributes']['typeString']}       
                accesspoints_position.append(accesspoint_position)
            except:
                print('INFO: no valid position for access point:', accesspoint['attributes']['name'])
    except:
        pass

    return accesspoints_position

def save_maps_from_floors(floors_ids):

    # Farbdefinitionen
    color_red = (255, 0, 0, 128) # red (3700 APs)
    color_orange = (230, 125, 0, 128) # orange (3800/4800 APs)
    color_black = (0, 0, 0, 128) # black (restliche APs)
    
    for floor_id in floors_ids:
        print("\nINFO: >>>>>>>>>>>>>>>>>> next floor >>>>>>>>>>>>>>>>>>")
        try:
            floor_details = get_floor_details(floor_id)

            floor_width = floor_details['geometry']['width']
            floor_height = floor_details['geometry']['length']
            
            building_name = floor_details['buildingName']
            map_name = floor_details['name']
            if floor_details['imageInfo']['generatedRasterImage'] == None:
                image_id = floor_details['imageInfo']['image']
            else:
                image_id = floor_details['imageInfo']['generatedRasterImage']
        except Exception as e:
            print('WARN:', e)

        try:
            # teils sind Bilder in Greyscale, deswegen gibts fehler, sobald rote Punkte/Schrift  
            # gezeichnet werden, deswegen wird das Bild nach "RGB" konvertiert
            try:
                image_map = Image.open(get_map_image(image_id)).convert("RGB")
            except Exception as e:
                print('WARN: failed to convert image to RGB:', e)
                print('WARN: image_id:', image_id)
    

            print("INFO: floor ID:", floor_id)
            map_image_width, map_image_height = image_map.size
            x_factor = map_image_width / floor_width
            y_factor = map_image_height / floor_height
            building_directory = map_folder + '/' + building_name
            create_directory(building_directory)
            draw = ImageDraw.Draw(image_map)
            accesspoints_position = get_accesspoints_position(floor_id)
            ap_position_length = len(accesspoints_position)

            print("INFO: AP count:", ap_position_length)

            if ap_position_length != 0:
                for accesspoint_position in accesspoints_position:
                    x = accesspoint_position['xcoordinate'] * x_factor
                    y = accesspoint_position['ycoordinate'] * y_factor
                    ap_name = accesspoint_position['name']
                    ap_type = accesspoint_position['ap_type']
                    try:
                        # red color for 3700 AP's
                        if "3700" in ap_type:
                            color = color_red
                        # red color for 3800/4800 AP's
                        elif "800" in ap_type:
                            color = color_orange
                        # black color for others
                        else:
                            color = color_black

                        draw.rounded_rectangle((x-5, y-5, x+5, y+5), radius=5, fill=color, width=5)
                        #draw.text((x-50, y+5), ap_name, fill=(255, 0, 0, 128), font=ubuntu_font)

                        #create image with text, rotate it 90 degrease and paste it to the map
                        textimg_width, textimg_height = ubuntu_font.getsize(ap_name)
                        text_img = Image.new('RGB', (textimg_width, textimg_height), color=(255, 255, 255, 255))
                        text_img_draw = ImageDraw.Draw(text_img)
                        text_img_draw.text((0, 0), ap_name, font=ubuntu_font, fill=color)
                        text_img_rotate = text_img.rotate(90, expand=1)
                        image_map.paste(text_img_rotate, box=(int(x - textimg_height/2)  ,int(y - textimg_width - 10)))

                      
                    except Exception as e:
                        print("ERROR: not able to draw on floor ID / AP:", map_name, "/", ap_name)
                        print("ERROR: exception:", e)

                # AP Color Legende oben links von jedem Plan
                draw.rounded_rectangle((45, 45, 55, 55), radius=5, fill=color_red, width=5)
                draw.text((60, 45), 'AP Typ: 3700 -> zu ersetzen', fill=color_red, font=ubuntu_font)

                draw.rounded_rectangle((45, 75, 55, 85), radius=5, fill=color_orange, width=5)
                draw.text((60, 75), 'AP Typ: 3800/4800 -> Lifecycle 2024/25 (in Planung)', fill=color_orange, font=ubuntu_font)

                draw.rounded_rectangle((45, 105, 55, 115), radius=5, fill=color_black, width=5)
                draw.text((60, 105), 'kein Lifecycle geplant', fill=color_black, font=ubuntu_font)

            else:
                print('WARN: no access points on map:', map_name)

            image_map.save(building_directory + '/' + map_name + '.jpg')
            print('INFO: image saved:', building_name, '/', map_name)
        except:
            print('WARN: no image found for building/floor:', building_name, '/', map_name)    


def delete_folder(map_folder):
    try:
        shutil.rmtree(map_folder)
        print('INFO: deleted folder', map_folder)
    except Exception as e:
        print('WARNING: could not delete folder', map_folder, e)
    
def delete_file(file_name):
    try:
        os.remove(file_name)
        print('INFO: deleted file', file_name)
    except Exception as e:
        print('WARNING: could not delete', file_name, e)

def create_zip(zip_name, map_folder):
    try:
        shutil.make_archive(zip_name, 'zip', map_folder)
    except Exception as e:
        print('ERROR: could not create ZIP file', e)


if __name__ == '__main__':
 
    # delete existing folder with maps
    delete_folder(map_folder)

    # delete ZIP file with maps
    delete_file(map_folder + '.zip')

    # get floors from CC
    floors = get_floorIDs_from_cc()

    # save maps based on CC floors to disk
    save_maps_from_floors(floors)

    # create zip file without date in filename
    zip_name = map_folder
    create_zip(zip_name, map_folder)

    # copy zip to EXTERNAL-SERVER, where the webservice for the CC Maps runs
    print('INFO: copy zip file to EXTERNAL-SERVER')
    process = subprocess.Popen(["scp", "-i", "/PATH/TO/YOUR/ssh_host_rsa_key", zip_name + '.zip', "USERNAME@EXTERNAL-SERVER:/PATH/TO/YOUR/vHOST/htdocs/"])
    sts = os.waitpid(process.pid, 0)

    # create zip file with date in filename, example cc_maps_2023-06-23.zip
    today = datetime.date.today()
    year = str(today.year)
    # format month/day to 2 digits (June is 06 instead of 6)
    month = '%02d' % today.month
    day = '%02d' % today.day
    zip_name = map_folder + '_' + year + '-' + month + '-' + day

    create_zip(zip_name, map_folder)

    # prepare commands which are executed on EXTERNAL-SERVER
    commands = [
        'rm -rf /PATH/TO/YOUR/vHOST/htdocs/cc_maps/*',
        'unzip -q -o /PATH/TO/YOUR/vHOST/htdocs/cc_maps.zip -d /PATH/TO/YOUR/vHOST/htdocs/cc_maps/',
    ]

    # initialize the SSH client
    client = paramiko.SSHClient()

    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname='EXTERNAL-SERVER.domain.name', username='USERNAME', key_filename='/PATH/TO/YOUR/ssh_host_rsa_key')
    except Exception as e:
        print("ERROR: Cannot connect to the SSH Server: ", e)
        exit()
    
    # execute the commands
    for command in commands:
        print('INFO: execute command:', command)
        stdin, stdout, stderr = client.exec_command(command)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print('ERROR:', err)
    