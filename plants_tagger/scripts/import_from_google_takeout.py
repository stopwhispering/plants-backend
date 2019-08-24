import glob
import json
import piexif
import datetime
import logging

# from collections import Set
from plants_tagger.util.exif_helper import decode_record_date_time, encode_record_date_time

# path = r'C:\temp\DCIM\takeout-2016\Takeout'
# path = r'C:\IDEs\sap-webide-personal-edition-1.53.5-trial\serverworkspace\my\myuser\OrionContent\tempMyFrontend\webapp\localService\original\DCIM\Google Takeouts 2016'
# path = r'C:\IDEs\sap-webide-personal-edition-1.53.5-trial\serverworkspace\my\myuser\OrionContent\tempMyFrontend\webapp\localService\original\DCIM\Google Takeouts 2017-01-01 bis 2017-06-18'
# path = r'C:\IDEs\sap-webide-personal-edition-1.53.5-trial\serverworkspace\my\myuser\OrionContent\tempMyFrontend\webapp\localService\original\DCIM\Google Takeouts 2015'
path = r'C:\temp\Google Takeouts 2015'

logger = logging.getLogger(__name__)

s1 = "Ã¤"  # ae
s2 = "Ã¼"  # ue
s3 = "Ã¶"  # oe
s4 = "Ãœ"  # Ue
s5 = "Ã„"  # Ae


def import_json_metadata_into_exif():
    paths_images = glob.glob(path+ '/**/*.jp*g', recursive=True)
# paths = glob.glob(path+ '/**/*.json', recursive=True)

    missing_json = []
    bad_chars_in_json = []

    for p in paths_images:
        exif_dict = piexif.load(p)
        if 270 in exif_dict['0th'] and not exif_dict['0th'][270].decode('utf-8').strip() == 'SONY DSC':
            current_desc = exif_dict['0th'][270].decode('utf-8')
            logger.info(f'a{exif_dict["0th"][270][:8]}b')
            logger.info(f'CURRENT DESCRIPTION!!!!!!!!!!!!!!!!!!!!!!! {current_desc}')
            continue
        else:
            try:
                with open(f'{p}.json', errors='ignore') as f:
                    meta = json.load(f)
            except FileNotFoundError:
                missing_json.append(p)
                continue
            desc: str = meta['description']
            if desc.strip():
                # treat umlaute
                desc = desc.replace(s1, 'ae')
                desc = desc.replace(s2, 'ue')
                desc = desc.replace(s3, 'oe')
                desc = desc.replace(s4, 'Ue')
                desc = desc.replace(s5, 'Ae')
                desc = desc.replace('â€', 'dead')
                desc = desc.replace('ÃŸ', 'ss')
                desc = desc.replace('â™°', '')
                # logger.info(desc)

                if desc.find('â™°') > 0:
                    _ = 1

                # remove line breaks
                desc = desc.replace('\n', '; ')

                logger.info(desc)

                # save in exif
                exif_dict['0th'][270] = desc.encode('utf-8')
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, p)

    logger.info('missing:')
    logger.info(missing_json)


def update_record_date():
    # oben wurde change date leider nicht wiederhergestellt. wenn kein record date gesetzt, wird change date
    # als record date gesetzt. --> record date anhand von json setzen
    paths_images = glob.glob(path + '/**/*.jp*g', recursive=True)
    for p in paths_images:

        exif_dict = piexif.load(p)
        date_exif = decode_record_date_time(exif_dict["Exif"][36867])

        try:
            with open(f'{p}.json', errors='ignore') as f:
                meta = json.load(f)
        except FileNotFoundError:
            logger.info(f'json missing: {p}')
            continue

        date_json = datetime.datetime.fromtimestamp(int(meta['photoTakenTime']['timestamp']))

        if date_exif != date_json:
            logger.info(f'{p} / {date_exif} / {date_json}')
            b_dt = encode_record_date_time(date_json)
            exif_dict['Exif'][36867] = b_dt
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, p)

        # logger.info(f'{date_exif} / {date_json} / {"OK" if date_exif == date_json else "NOT OK"}')

# import_json_metadata_into_exif()
update_record_date()
_ = 1
