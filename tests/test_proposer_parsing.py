from app.adaptive.proposer import _parse_response


def test_parse_response_extracts_valid_proposals():
    raw = """```json
    {
      "proposals": [
        {"base": "ma_crossover", "params": {"fast": 8, "slow": 21}, "rationale": "short EMA"},
        {"base": "rsi_reversion", "params": {"period": 7, "oversold": 25, "overbought": 75},
         "rationale": "high freq mean reversion"}
      ]
    }
    ```"""
    p = _parse_response(raw)
    assert len(p) == 2
    assert {x["base"] for x in p} == {"ma_crossover", "rsi_reversion"}


def test_parse_response_rejects_unknown_base():
    raw = '{"proposals":[{"base":"hack_db","params":{},"rationale":"x"},' \
          '{"base":"ma_crossover","params":{"fast":10,"slow":30},"rationale":"ok"}]}'
    p = _parse_response(raw)
    assert len(p) == 1 and p[0]["base"] == "ma_crossover"


def test_parse_response_handles_garbage():
    assert _parse_response("not json") == []
    assert _parse_response('{"proposals": "not a list"}') == []
    assert _parse_response("") == []


def test_parse_response_caps_count():
    proposals = [{"base": "ma_crossover", "params": {"fast": i, "slow": i+20},
                  "rationale": f"r{i}"} for i in range(20)]
    raw = f'{{"proposals": {str(proposals).replace(chr(39), chr(34))}}}'
    p = _parse_response(raw)
    assert len(p) == 10  # обрезается до 10
