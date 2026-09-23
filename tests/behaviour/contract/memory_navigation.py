def memory_navigation(c):
    from frame_oracle import render
    import base64
    c.configure();c.enc(1,-2);c.screen_header('Ch. 1 Memory')
    baseline=[(60,127),(62,117),(64,107),(65,97)]
    first=[(72,90),*baseline[1:]]
    both=[(72,90),(76,80),*baseline[2:]]
    branch=[(72,90),(62,117),(79,70),(65,97)]
    def counter(current,total):
        expected=render([(0,23,15,str(current)),(0,49,15,str(total))],font_size=10,antialias=1)
        indexes=[(y*128+x)*4+k for y in list(range(13,26))+list(range(39,52)) for x in range(16) for k in range(3)]
        def match(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[i]==expected[i] for i in indexes)
        c.wait(match);c.results.append(dict(kind='memory-position',current=current,total=total,frame_matched=True))
    def phrase(values):c.playback([(1,[144,n,v]) for n,v in values],cycles=2)
    def record(step,note,velocity):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.action(type='midi',port=1,bytes=[144,note,velocity]);c.elapse(.05)
            c.action(type='midi',port=1,bytes=[128,note,0])
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.1)
    counter(0,0);c.key(2);c.key(3);c.enc(3,-3);c.enc(3,3);counter(0,0);phrase(baseline)
    c.enc(1,-2);c.screen_header('Ch. 1 Note Masks');record(1,72,90);record(2,76,80)
    c.enc(1,2);counter(2,2);phrase(both)
    c.enc(3,-1);counter(1,2);phrase(first)
    c.enc(3,-1);counter(0,2);phrase(baseline)
    c.enc(3,-3);counter(0,2);phrase(baseline)
    c.enc(3,1);counter(1,2);phrase(first)
    c.enc(3,1);counter(2,2);phrase(both)
    c.enc(3,3);counter(2,2);phrase(both)
    c.key(2);counter(0,2);phrase(baseline)
    c.key(3);counter(2,2);phrase(both)
    c.enc(3,-1);counter(1,2)
    c.enc(1,-2);record(3,79,70);c.enc(1,2);counter(2,2);phrase(branch)
    c.key(3);counter(2,2);phrase(branch)
    c.key(2);counter(0,2);phrase(baseline)
    c.key(3);counter(2,2);phrase(branch)
