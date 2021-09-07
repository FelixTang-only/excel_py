from numpy.lib import twodim_base
import pandas as pd
# # a = pd.read_excel('/Users/apple/Downloads/商户后台-系统操作界面完整版9.2 (最终).xls', header=0, usecols=[1], names=None, keep_default_na=False)
a = pd.read_excel('/Users/apple/Downloads/商户后台-系统操作界面完整版9.2 (最终).xls', header=0, names=None, keep_default_na=False)
a_li = a.values.tolist()

# 将国际化en.js英文文件中的value值改成首字母大写，效果
excel_index = 3 # 要替换的excel对应的列索引
miss_out_file_path = '/Users/apple/Downloads/miss_out.js'
# to_file_path = '/Users/apple/Downloads/vi.js'
to_file_path = '/Users/apple/Downloads/zh-TW.js'
from_file_path = '/Users/apple/Downloads/zh-CN.js'

def test():
    # a = ':'
    sp_str = "\'"
    # f_new = open('/Users/apple/Downloads/zh-TW.js', 'w+', encoding='utf-8')
    f_new = open(to_file_path, 'w+', encoding='utf-8')
    miss_out = open(miss_out_file_path, 'w+', encoding='utf-8')
    with open(from_file_path, 'r', encoding='utf8') as f:
        for inl, line in enumerate(f):
            # print('1: ', line)
            # if((a in line) and ('{' not in line) and ('}' not in line)):
            if sp_str in line and "'" in line:
                # tempOne = line.split(a)[0]
                temp = line
                # tempTwo = line.split(sp_str)[1].split("\'")[1]
                tempTwo = line.split(sp_str)[1]
                # if inl == 522:
                #     print(tempTwo)
                #     break
                # else:
                #     continue
                
                for inx, x in enumerate(a_li):
                    # if x[1] != '' and x[1] in temp:
                    if x[1] != '' and x[1] == tempTwo:
                        temp = temp.replace(x[1], x[excel_index])
                        print(temp)
                        f_new.write(temp)
                        break
                    if inx == len(a_li) - 1:
                        f_new.write(temp)
                        miss_out.write(temp)
                # f_new.write(tempOne + ': ' + (' ').join(tempTwo))
            else:
                f_new.write(line)


test()
