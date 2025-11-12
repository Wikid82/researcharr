from xml.etree import ElementTree as ET
p='artifacts/pairwise/random_12.xml'
try:
    t=ET.parse(p)
except Exception as e:
    print('Failed to parse',p, e); raise
root=t.getroot()
files=[]
for tc in root.findall('.//testcase'):
    cls=tc.get('classname')
    if not cls: continue
    path = cls.replace('.', '/') + '.py'
    files.append(path)
    if tc.find('failure') is not None:
        break
open('/work/ordering.txt','w').write('\n'.join(files))
print('Wrote ordering.txt with', len(files), 'files')
