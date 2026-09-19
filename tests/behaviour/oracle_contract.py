"""Repeated text drawing must not use freed FreeType faces in Cairo's cache."""
from frame_oracle import render,header

def main():
    labels=['DEVICES > ','MODS >','macro 1','Fixed Note','1.00']
    expected={text:render([(0,30,15,text)]) for text in labels}
    for iteration in range(200):
        header('Ch. 1 Device Config')
        for text in labels:
            assert render([(0,30,15,text)])==expected[text],(iteration,text)
    print('1200 repeated Cairo/font draws stable')
if __name__=='__main__':main()
