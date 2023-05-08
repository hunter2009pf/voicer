import os


class FileUtil:
    @staticmethod
    def get_text_from_file(file_path):
        if os.path.exists(file_path):
            print('The file exists')
            # open the file in read-only mode
            with open(file_path, 'r') as f:
                # read the contents of the file
                text = f.read()
            # print the contents of the file
            return text
        else:
            print('The file does not exist')
            return ""
