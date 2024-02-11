ID_NOT_FOUND = -1
db: list[int, list[int]] = []


def log_msg_ids_correspondence(vk_msg_id: int, tg_msg_id: int):
    print("logging:", vk_msg_id, "in vk is", tg_msg_id, "in tg")
    existing_record_in_db_id = get_index_in_db(vk_msg_id)
    if existing_record_in_db_id == ID_NOT_FOUND:
        db.append([vk_msg_id, [tg_msg_id]])
    else:
        db[existing_record_in_db_id][1].append(tg_msg_id)


def find_corresponding_tg_id(vk_msg_id: int) -> int:
    for a in db:
        if a[0] == vk_msg_id:
            return a[1]
    return ID_NOT_FOUND


def get_index_in_db(vk_msg_id: int) -> int:
    for i in range(len(db)):
        if db[i][0] == vk_msg_id:
            return i
    return ID_NOT_FOUND
