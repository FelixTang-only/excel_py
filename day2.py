# 读取Excel文件
import pandas as pd
a = pd.read_excel('/Users/apple/Work/excel_py/day2.xlsx', header=1)
print(a)

a.columns = ['id', '年龄', '名字', '成绩']
print(a.columns)
a = a.set_index('id')
a.to_excel('/Users/apple/Work/excel_py/day2-output.xlsx')
