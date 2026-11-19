"""R1 tooling (eval/real_data.py): labels.csv checks and the recording sheet, no GPU."""

import pytest

from eval import real_data

HEADER = "file,kind,truth,subtype,text,distance_cm,light,split\n"


def test_labels_are_read_and_photo_truth_is_split(tmp_path):
    p = tmp_path / "labels.csv"
    p.write_text(HEADER + "photo/a.jpg,photo,person+package,,,150,night,test\n"
                 "photo/b.jpg,photo,empty,,,,day,tune\n"
                 "voice/c.wav,voice,DELIVERY,PARCEL,택배 왔습니다,50,,test\n", encoding="utf-8")
    rows = real_data.load_labels(p)
    assert rows[0].photo_labels() == {"person", "package"} and rows[1].photo_labels() == set()
    assert rows[2].truth == "DELIVERY" and rows[2].distance_cm == "50"


def test_bad_rows_are_refused_with_their_line_numbers(tmp_path):
    p = tmp_path / "labels.csv"
    p.write_text(HEADER + "photo/a.jpg,photo,box,,,,day,test\n"
                 "voice/c.wav,voice,DELIVERYY,,x,20,,test\n"
                 "voice/d.wav,voice,PICKUP,,x,20,,maybe\n", encoding="utf-8")
    with pytest.raises(ValueError) as err:
        real_data.load_labels(p)
    message = str(err.value)
    assert "2행" in message and "3행" in message and "4행" in message


def test_sheet_reads_the_held_out_sentences_as_test_at_every_distance():
    sheet, labels = real_data.make_sheet([20, 100])
    test = [r for r in labels if r["split"] == "test"]
    tune = [r for r in labels if r["split"] == "tune"]
    assert len(test) == 45 * 2  # every 김덕민 sentence at both distances
    assert len(tune) == 9 * 3 * 2  # 3 dev sentences per purpose
    assert {r["distance_cm"] for r in labels} == {"20", "100"}
    assert "voice/d_delivery_01_20cm.wav" in {r["file"] for r in labels}
    assert "d_delivery_01_<거리>cm.wav" in sheet
