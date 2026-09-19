"""Memory K1+K3 / K1+K2: jump, then forget the history (README Memory section)."""

def memory_truncate(c):
    from frame_oracle import render
    import base64
    c.configure();c.enc(1,-2);c.screen_header('Ch. 1 Memory')
    baseline=[(60,127),(62,117),(64,107),(65,97)]
    first=[(72,90),*baseline[1:]]
    both=[(72,90),(76,80),*baseline[2:]]
    third=[(72,90),(76,80),(79,70),(65,97)]
    def counter(current,total):
        expected=render([(0,23,15,str(current)),(0,49,15,str(total))],font_size=10,antialias=1)
        indexes=[(y*128+x)*4+k for y in list(range(13,26))+list(range(39,52)) for x in range(16) for k in range(3)]
        def match(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[i]==expected[i] for i in indexes)
        c.wait(match);c.results.append(dict(kind='memory-position',current=current,total=total,frame_matched=True))
    def phrase(label,values):
        c.playback([(1,[144,n,v]) for n,v in values],cycles=2)
        c.results.append(dict(kind='memory-truncate-phrase',stage=label,notes=values,passed=True))
    def record(step,note,velocity):
        c.enc(1,-2);c.screen_header('Ch. 1 Note Masks')
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.action(type='midi',port=1,bytes=[144,note,velocity]);c.elapse(.05)
            c.action(type='midi',port=1,bytes=[128,note,0])
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.1);c.enc(1,2);c.screen_header('Ch. 1 Memory')
    def shift(n):
        # norns passes K1 to the script only after its 0.25 s menu threshold.
        c.action(type='key',n=1,state=1)
        try:c.elapse(.4);c.key(n)
        finally:c.action(type='key',n=1,state=0)
        c.elapse(.1)
    counter(0,0);phrase('baseline',baseline)
    record(1,72,90);record(2,76,80);counter(2,2);phrase('two-edits',both)
    c.enc(3,-1);counter(1,2);phrase('undone-to-first',first)
    # K1+K3 from the middle: apply the latest action, then forget all history.
    shift(3);counter(0,0);phrase('shift-K3-applied',both)
    c.enc(3,-1);counter(0,0);phrase('forgotten-E3-inert',both)
    c.key(2);counter(0,0);phrase('forgotten-K2-inert',both)
    # A new action starts a fresh history whose beginning is the applied state.
    record(3,79,70);counter(1,1);phrase('fresh-history',third)
    # K1+K2: return to the beginning of this history, then forget it.
    shift(2);counter(0,0);phrase('shift-K2-undone',both)
    c.key(3);counter(0,0);phrase('forgotten-K3-inert',both)
    c.enc(3,1);counter(0,0);phrase('forgotten-E3-forward-inert',both)
    # K1+K2 from the middle of a two-action history also returns to its start.
    record(3,79,70);record(4,84,60);counter(2,2)
    c.enc(3,-1);counter(1,2);phrase('second-history-middle',third)
    shift(2);counter(0,0);phrase('shift-K2-from-middle',both)
