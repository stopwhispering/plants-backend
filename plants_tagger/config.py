import os

# connection_string = 'sqlite:///dev.sqlite'
connection_string = 'sqlite:///C:\\temp\\database.db'

path_frontend_temp = r"C:\IDEs\sap-webide-personal-edition-1.53.5-trial\serverworkspace\my\myuser\OrionContent" \
                     r"\plants_tagger\webapp"

path_frontend = r"C:\IDEs\sap-webide-personal-edition-1.53.5-trial\serverworkspace\my\myuser\OrionContent" \
                r"\PlantsTaggerFrontend\webapp"

path_uploaded_photos_original = r'C:\IDEs\sap-webide-personal-edition-1.53.5-trial\serverworkspace\my\myuser' \
                                r'\OrionContent\plants_tagger\webapp\localService\original\uploaded'
if not os.path.exists(path_uploaded_photos_original):
    os.makedirs(path_uploaded_photos_original)

folder_root_original_images = r'C:\IDEs\sap-webide-personal-edition-1.53.5-trial\serverworkspace\my\myuser\OrionContent\plants_tagger\webapp\localService\original'

rel_folder_photos_original = r"localService\original"
rel_folder_photos_generated = r"localService\generated"

size_preview_image = (300, 300)

size_thumbnail_image = (350, 350)

filter_hidden = True
