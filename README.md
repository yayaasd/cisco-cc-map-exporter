## Cisco Catalyst Center Map Exporter

started building another python tool due to migration from Prime Infrastructure to Catalyst Center.

### Capabilities
We build a possibility to change the color of the APs based on device model. Useful for lifecycle or capacity planning.

#### Example
![image](https://github.com/user-attachments/assets/be9f34cc-d49a-49df-8be9-fb2c6fcb2cf0)

### Warranty
Tool is provided as is and no adjustments promised. Use at your own risk!

### Compatibility
Tested on Catalyst Center 2.3.7.6.
Please take note, that due to limited api documantation, we were forced to use internal api's. These may could change with next updates of CC.

## Install
1. git clone to your server
```
git clone https://github.com/yayaasd/cisco-cc-map-exporter.git cisco-cc-map-export
```
3. edit device_credentials_template.py and save as device_credentials.py
```
cc = {
        "hostname": "catalystcenter.domain.name",
        "user": "USER",
        "password": "PASS"
     }
```
4. install python environment (see requirements.txt)
```
pip install -r requirements.txt
```
5. adjust the path/user in the script (simply search for these strings):
```
/PATH/TO/YOUR/FOLDER/
/PATH/TO/YOUR/ssh_host_rsa_key
username@EXTERNAL-SERVER:/PATH/TO/YOUR/vHOST/htdocs/
hostname=''
username='USERNAME'
```
7. add cronjob (keep in mind, the script could take some time)
```
0 3 * * * python /PATH/TO/YOUR/FOLDER/cc-map-exporter.py >> /var/log/cronjob_cc-map-exporter.log 2>&1
```