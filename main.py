import glob
import json
from script.get_wechat_key import Wechat
from script.decrypt import decrypt
from script.decrypt import encrypt
from script.merge import merge_databases
from script.merge_table import merge_table
from script.compress_content import file
from export_excel import *
import pymem.process
from pymem import Pymem
import shutil
import win32com.shell.shell as shell
import win32com.shell.shellcon as shellcon


def check_key():
    file_name = f"key.txt"  # 创建存放key的文件

    # 检查文件是否存在
    if not os.path.exists(file_name):
        # 如果文件不存在，创建它
        with open(file_name, "w"):
            pass  # 创建空文件
        print(f"文件 {file_name} 已在当前目录下创建。")
    else:
        print(f"文件 {file_name} 已经存在于当前目录。")


def check_dir_file(path, file_path):
    if not os.path.exists(path):  # 检查目录是否存在，不存在则创建
        os.makedirs(path)

    if not os.path.exists(file_path):  # 检查文件是否存在，不存在则创建
        with open(file_path, 'w'):
            # 可以在此处写入一些初始化内容到文件，如果没有内容可写，pass即可
            pass
        print(f"文件 '{file_path}' 已创建。")
    else:
        print(f"文件 '{file_path}' 已经存在。")


def get_key():
    try:
        wechat = Pymem("WeChat.exe")
        key = Wechat(wechat).GetInfo()
        with open("key.txt", "w") as file:
            file.write(key)
    except pymem.exception.ProcessNotFound:
        print("微信未登录")
        # input("按任意键退出...")
        exit(0)
    except pymem.exception.CouldNotOpenProcess:
        print("权限不足")
        # input("按任意键退出...")
        exit(0)
    except Exception as e:
        print(e)
        # input("按任意键退出...")
        exit(0)


def get_wx_location():
    # 获取当前用户名
    users = os.path.expandvars('$HOMEPATH')

    # 找到3ebffe94.ini配置文件
    with open(r'C:' + users + '\\AppData\\Roaming\\Tencent\\WeChat\\All Users\\config\\3ebffe94.ini') as f:
        f = f.read()

    # 读取文件将路径放到wx_location变量里
    if f == 'MyDocument:':
        # 获取特定用户的个人文档文件夹路径
        pidl = shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_PERSONAL)
        my_documents_path = shell.SHGetPathFromIDList(pidl).decode('utf-8')

        wx_location = my_documents_path + '\\WeChat Files'
    else:
        wx_location = f + "\\WeChat Files"
    return wx_location


def get_path_decrypt_merge():
    wx_location = get_wx_location()
    if not os.path.isdir(wx_location):
        print(f'文件夹不存在:{wx_location}')
        exit(0)

    # 列出目录下所有文件夹
    for user_folder_name in os.listdir(wx_location):
        if os.path.isdir(os.path.join(wx_location, user_folder_name)):
            if 'All Users' in user_folder_name or 'Applet' in user_folder_name or 'WMPF' in user_folder_name:
                continue
            elif 'wxid_' in user_folder_name:
                # dir_msg_path 原来是 contact_path
                dir_msg_path = os.path.join(wx_location, user_folder_name, 'Msg')
                # dir_multi_path 原来是 msg_path
                dir_multi_path = os.path.join(wx_location, user_folder_name, 'Msg', 'Multi')
                if not os.path.exists(dir_msg_path) and not os.path.exists(dir_multi_path):
                    print(f'文件夹不存在:{dir_msg_path} {dir_multi_path}')
                    exit(0)
                decrypt_db(dir_msg_path, dir_multi_path, user_folder_name)
            else:
                contact_path_input = input('未找到"wxid_"开头的目录,请手动输入文件夹名称:')
                dir_msg_path = os.path.join(wx_location, contact_path_input, 'Msg')
                dir_multi_path = os.path.join(wx_location, contact_path_input, 'Msg', 'Multi')
                if not os.path.exists(dir_msg_path) and not os.path.exists(dir_multi_path):
                    print(f'文件夹不存在:{dir_msg_path} {dir_multi_path}')
                    exit(0)
                decrypt_db(dir_msg_path, dir_multi_path, contact_path_input)
                break


def decrypt_db(dir_msg_path, dir_multi_path, user_folder_name):
    with open('key.txt', 'r') as f:
        key = f.read()
    file_micromsg_path = dir_msg_path + '\\MicroMsg.db'
    decrypt_user_folder = f'.\\db\\{user_folder_name}'
    decrypt_micromsg_path = os.path.join(decrypt_user_folder, 'MicroMsg.db')
    check_dir_file(decrypt_user_folder, decrypt_micromsg_path)  # 检测文件文件夹是否存在，不存在则创建

    decrypt(key, file_micromsg_path, decrypt_micromsg_path)  # 解码数据库
    msg_files = glob.glob(os.path.join(dir_multi_path, 'MSG*.db'))
    for _file_name in msg_files:
        if os.path.isfile(_file_name):
            try:
                file_name = os.path.basename(_file_name)
                msg_db_path = os.path.join(dir_multi_path, file_name)
                check_dir_file(decrypt_user_folder, os.path.join(decrypt_user_folder, file_name))
                decrypt(key, msg_db_path, os.path.join(decrypt_user_folder, file_name))
            except Exception as e:
                print(e)
    try:
        merge_db(user_folder_name)  # 合并数据库
    except Exception as e:
        print('非当前登录微信数据库,无法合并,跳过...')


def read_all_files_in_directory(directory_path):
    """
    读取指定目录下的所有文件。
    参数:
    directory_path (str): 要读取的目录的路径。
    返回:
    files_list (list[str]): 目录中所有文件的完整路径列表。
    """
    files_list = []
    for item in os.listdir(directory_path):
        # 构建完整的文件/子目录路径
        full_item_path = os.path.join(directory_path, item)

        # 检查是否为文件（而非目录）
        if os.path.isfile(full_item_path):
            files_list.append(full_item_path)

    return files_list


def merge_db(user_folder):
    source_databases = read_all_files_in_directory(f'db\\{user_folder}')
    # 源数据库文件列表
    # source_databases = [f"db\\{user_folder}\\MSG1.db", f"db\\{user_folder}\\MSG2.db", f"db\\{user_folder}\\MSG3.db",
    #                     f"db\\{user_folder}\\MSG4.db", f"db\\{user_folder}\\MSG5.db", f"db\\{user_folder}\\MicroMsg.db"]
    # 目标数据库文件
    target_database = f"db\\{user_folder}\\MSG.db"

    shutil.copy(f'db\\{user_folder}\\MSG0.db', target_database)  # 使用MSG0.db数据库文件作为模板
    merge_databases([item for item in source_databases if 'MicroMsg.db' not in item and 'MSG0.db' not in item],
                    target_database)  # 合并数据库,列表推导式,排除MicroMsg.db、MSG0.db文件
    merge_table(f"db\\{user_folder}\\MicroMsg.db", target_database, ['Contact', 'ChatRoom'])  # 将两个库文的表合成一个文件
    # remove_db(source_databases)  # 删除文件


def remove_db(file_paths):
    for file_path in file_paths:
        print(f"正在清理 {file_path}...")
        try:
            os.remove(file_path)
            print(f"{file_path} 已清理。")
        except FileNotFoundError:
            print(f"错误：文件 {file_path} 未找到。")
        except PermissionError:
            print(f"错误：没有足够的权限删除 {file_path}。")
        except Exception as e:
            print(f"删除文件时发生错误：{e}")


def remove_dir(dir_paths):
    for dir_path in dir_paths:
        print(f"正在清理 {dir_path}...")
        try:
            shutil.rmtree(dir_path)
            print(f"{dir_path} 已清理。")
        except FileNotFoundError:
            print(f"错误：目录 {dir_path} 未找到。")
        except PermissionError:
            print(f"错误：没有足够的权限删除 {dir_path}。")
        except Exception as e:
            print(f"删除目录时发生错误：{e}")


if __name__ == '__main__':
    remove_db(['.\\key.txt'])  # 删除db文件夹和key.txt文件
    remove_dir(['.\\db'])

    check_key()  # 检查存放key文件是否存在
    get_key()  # 获取key
    get_path_decrypt_merge()  # 自动获取路径，解密，合并数据库
    wxids = get_wxid()


    while True:
        # 导出为excel
        for wx in wxids:  # 多个微信号,循环处理
            try:
                all_data = get_data(wx)
            except Exception as e:
                print('当前处理数据库非当前登录微信,跳过...', e)
                continue
            deal_over_data = deal_data(all_data, wx)
            # json_string = json.dumps(deal_over_data)
            # print(json_string)
            write_excel(deal_over_data, wx)
        break
    remove_db(['.\\key.txt'])  # 删除db文件夹和key.txt文件
    remove_dir(['.\\db'])
    # input('导出完成,按任意建关闭...')
