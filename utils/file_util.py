import os


class FileUtil:
    voicer_root_dir_path = ""
    asr_dir_path = ""

    @staticmethod
    def get_text_from_file(file_path):
        if os.path.exists(file_path):
            print('The file exists')
            # open the file in read-only mode
            with open(file_path, 'r', encoding='utf-8') as f:
                # read the contents of the file
                text = f.read()
            # print the contents of the file
            return text
        else:
            print('The file does not exist')
            return ""

    @staticmethod
    def create_data_storage_dir():
        # Get the path to the "AppData/Roaming" directory
        appdata_path = os.getenv('APPDATA')

        # Create the directory path
        FileUtil.voicer_root_dir_path = os.path.join(appdata_path, 'voicer')
        # Create the directory if it doesn't exist
        if not os.path.exists(FileUtil.voicer_root_dir_path):
            os.makedirs(FileUtil.voicer_root_dir_path)

        # Save data to a file within the created directory
        FileUtil.asr_dir_path = os.path.join(FileUtil.voicer_root_dir_path, 'asr')
        if not os.path.exists(FileUtil.asr_dir_path):
            os.makedirs(FileUtil.asr_dir_path)

    @staticmethod
    def get_asr_storage_dir():
        return FileUtil.asr_dir_path
