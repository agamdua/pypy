import autopath

objspacename = 'std'

class AppTestUserObject:
    def test_dictproxy(self):
        class NotEmpty(object):
            a = 1
        assert isinstance(NotEmpty.__dict__, dict) == False
        assert 'a' in NotEmpty.__dict__
        assert 'a' in NotEmpty.__dict__.keys()
        assert 'b' not in NotEmpty.__dict__
        assert isinstance(NotEmpty.__dict__.copy(), dict)
        assert NotEmpty.__dict__ == NotEmpty.__dict__.copy()
        try:
            NotEmpty.__dict__['b'] = 1
        except:
            pass
        else:
            raise AssertionError, 'this should not have been writable'

    def test_dictproxyeq(self):
        class a(object):
            pass
        class b(object):
            stuff = 42
        class c(object):
            stuff = 42
        assert a.__dict__ == a.__dict__
        assert a.__dict__ != b.__dict__
        assert a.__dict__ != {'123': '456'}
        assert {'123': '456'} != a.__dict__
        assert b.__dict__ == c.__dict__
