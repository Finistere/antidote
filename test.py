from antidote import inject, new_container

c = new_container()


class Service:
    pass


c[Service] = Service()


@inject(container=new_container())
def f(x: Service):
    return x


f()
