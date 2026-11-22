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
baselines. It comes with unit tests and a smoke command. It is not a result: no hypothesis has been tested yet. The
pre-registered tests G1–G8 and the author's thesis T-1 come in v0.2. The implementation spec, including the revisions
made before any freeze, is in [`SPEC.md`](SPEC.md).

```
py -m unittest discover -s tests
py -m tesaron.smoke --world-seed 900001 --encoder-seed 900101
```

Requires Python ≥ 3.12 and numpy.

## License and author

MIT, see [`LICENSE`](LICENSE). Author: Hazar Şimşek (GitHub: Mukanto), hazar.simsek.research@gmail.com.
