"""Entry point for `python -m aviary_kernel` (used by the kernelspec)."""

from ipykernel.kernelapp import IPKernelApp

from .kernel import AviaryKernel


def main() -> None:
    IPKernelApp.launch_instance(kernel_class=AviaryKernel)


if __name__ == "__main__":
    main()
