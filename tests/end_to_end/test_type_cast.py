from antidote import const, Constants, world


def test_run_me() -> None:
    with world.test.empty():
        world.singletons.add('test', [])
        world.get[list]('test').append(1)
        world.lazy[list]('test').get().append(2)

        world.get('test').append(1)

        class Conf(Constants):
            A = const[list]("a")

            def get(self, key):
                return []

        Conf().A.append(1)
