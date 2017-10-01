from blood import util


def test_to_snake_case():
    """
    Source: https://gist.github.com/jaytaylor/3660565
    """
    assert util.to_snake_case('snakesOnAPlane') == 'snakes_on_a_plane'
    assert util.to_snake_case('SnakesOnAPlane') == 'snakes_on_a_plane'
    assert util.to_snake_case('snakes_on_a_plane') == 'snakes_on_a_plane'
    assert util.to_snake_case('IPhoneHysteria') == 'i_phone_hysteria'
    assert util.to_snake_case('iPhoneHysteria') == 'i_phone_hysteria'


def test_to_CamelCase():
    """
    Source: https://gist.github.com/jaytaylor/3660565
    """
    assert util.to_CamelCase('snakes_on_a_plane') == 'SnakesOnAPlane'
