# Tesaron

Tesaron is a research prototype that turns semantic information into data and back. It then checks three things: whether
the encoded meaning is preserved, whether it becomes correct information, and whether it can be extended validly.
Shannon (encoder, channel, decoder) and Turing (computability and termination) inspired the design.

- **Encoder:** selects data stochastically within a context and assigns fuzzy membership degrees. A membership degree
  is a degree of belonging, never a probability.
- **Meaning unit:** an atom with a degree of support μ⁺ and a degree of refutation μ⁻.
- **Interface:** maps (μ⁺, μ⁻) to Belnap's four values: true, false, both, unknown.
- **Decoder:** two-channel Datalog with deterministic, terminating deduction, plus single-step abduction whose results
  stay hypotheses.
- **Criterion:** constrained Pareto over the share of new true and new false conclusions, measured against reference
  worlds whose meaning is known by construction.
- **Audit layer:** [Truth_Gate](https://github.com/Mukanto/truth_gate), pinned at `v0.5.1` as a separate dependency.

Something being computable does not make it true. Tesaron measures truth only against an external reference.

## Status

v0.1 is the core pipeline: world generator, encoder, Belnap interface, decoder, metrics, constrained Pareto and
baselines. It comes with unit tests and a smoke command. The implementation spec, including the revisions made before
any freeze, is in [`SPEC.md`](SPEC.md).

v0.2 is the pre-registration of the tests G1–G8 and of the author's thesis in the form T-1:
[`prereg/PREREG_v0.2.md`](prereg/PREREG_v0.2.md), with its audit layer in [`audit/`](audit/). It was reviewed blind
three times ([`prereg/reviews/`](prereg/reviews/)) and frozen by the manifest `prereg/FREEZE_v0.2.json`; the freeze
record is [`prereg/FREEZE_RECORD.md`](prereg/FREEZE_RECORD.md). It is not a result: the calibration and test worlds
are drawn only after the freeze, and no test has been run on them yet.

```
py -m unittest discover -s tests
py -m tesaron.smoke --world-seed 900001 --encoder-seed 900101
```

Requires Python ≥ 3.12 and numpy.

## License and author

MIT, see [`LICENSE`](LICENSE). Author: Hazar Şimşek (GitHub: Mukanto), hazar.simsek.research@gmail.com.
