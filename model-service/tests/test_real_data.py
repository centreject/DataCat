"""R1 tooling (eval/real_data.py): labels.csv checks and the recording sheet, no GPU."""

from types import SimpleNamespace

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


@pytest.mark.parametrize(
    "line",
    [
        ",photo,empty,,,,day,test",  # no file: would open data/real/ itself
        "voice/c.wav,voice,DELIVERY,,,20,,test",  # no text: the error rate would be meaningless
        "voice/c.wav,voice,DELIVERY,PIZZA,x,20,,test",  # not a DELIVERY subtype
        "voice/c.wav,voice,PICKUP,PARCEL,x,20,,test",  # PICKUP has no subtypes
        "photo/a.jpg,photo,package,PARCEL,,,day,test",  # photos carry no subtype
    ],
)
def test_rows_the_evaluation_would_miscount_are_refused(tmp_path, line):
    p = tmp_path / "labels.csv"
    p.write_text(HEADER + line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="2행"):
        real_data.load_labels(p)


def test_sheet_reads_the_held_out_sentences_as_test_at_every_distance():
    sheet, labels = real_data.make_sheet([20, 100])
    test = [r for r in labels if r["split"] == "test"]
    tune = [r for r in labels if r["split"] == "tune"]
    assert len(test) == 45 * 2  # every 김덕민 sentence at both distances
    assert len(tune) == 9 * 3 * 2  # 3 dev sentences per purpose
    assert {r["distance_cm"] for r in labels} == {"20", "100"}
    assert "voice/d_delivery_01_20cm.wav" in {r["file"] for r in labels}
    assert "d_delivery_01_<거리>cm.wav" in sheet


def test_voice_subtype_denominator_includes_misclassified_purpose():
    # Matches eval.metrics.subtype_accuracy: a DELIVERY/PARCEL utterance that ends up UNKNOWN
    # (e.g. NO_SPEECH) must count as a subtype miss (1/2 = 50%), not be dropped (1/1 = 100%).
    r1 = real_data.Row("voice/a.wav", "voice", "DELIVERY", "PARCEL", "택배 왔습니다", "20", "", "tune")
    r2 = real_data.Row("voice/b.wav", "voice", "DELIVERY", "PARCEL", "택배 두고 갑니다", "50", "", "tune")
    g1 = SimpleNamespace(purpose="DELIVERY", subtype="PARCEL")
    g2 = SimpleNamespace(purpose="UNKNOWN", subtype=None)
    lines = real_data.format_voice_results([(r1, "택배 왔습니다", g1), (r2, "", g2)], show_errors=True)
    total_row = next(line for line in lines if line.startswith("| 전체 |"))
    cells = [c.strip() for c in total_row.strip("|").split("|")]
    assert cells[4] == "1/2 (50%)"  # 용건 정확도
    assert cells[5] == "1/2 (50%)"  # 배송 세부 유형
    assert any("voice/b.wav" in line and "DELIVERY/PARCEL" in line and "(빈 받아쓰기)" in line for line in lines)


def test_photo_errors_lists_only_wrong_photos():
    ok_row = real_data.Row("photo/ok.jpg", "photo", "person+package", "", "", "50", "day", "tune")
    miss_row = real_data.Row("photo/miss.jpg", "photo", "person", "", "", "100", "night", "tune")
    fp_row = real_data.Row("photo/fp.jpg", "photo", "empty", "", "", "50", "day", "tune")
    lines = real_data.format_photo_results(
        [(ok_row, {"person", "package"}), (miss_row, set()), (fp_row, {"package"})],
        show_errors=True,
    )
    error_lines = lines[lines.index("#### 틀린 사진 (tune만)") :]
    assert not any("photo/ok.jpg" in line for line in error_lines)
    assert any("photo/miss.jpg" in line and "| person | empty |" in line for line in error_lines)
    assert any("photo/fp.jpg" in line and "| empty | package |" in line for line in error_lines)
