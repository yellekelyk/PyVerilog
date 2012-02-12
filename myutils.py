def cleanget(dictionary, key):
    val = dict()
    if key in dictionary:
        val = dictionary.get(key)
    return val
