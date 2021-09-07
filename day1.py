# pandas创建文件
import pandas as pd

d = {'id': [0, 1], 'name': ['kim', 'max']}
df = pd.DataFrame(data=d)
print(df)
df = df.set_index('id')
df.to_excel('/Users/apple/Work/excel_py/output.xlsx')
