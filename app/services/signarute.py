from inspect import Parameter, Signature


class SignatureHelper:
    @staticmethod
    def augment(signature: Signature, *extra: Parameter) -> Signature:
        if not extra:
            return signature

        parameters = list(signature.parameters.values())
        variadic_keyword_params: list[Parameter] = []
        while parameters and parameters[-1].kind is Parameter.VAR_KEYWORD:
            variadic_keyword_params.append(parameters.pop())

        return signature.replace(parameters=[*parameters, *extra, *variadic_keyword_params])

    @staticmethod
    def locate_param(sig: Signature, dep: Parameter, to_inject: list[Parameter]) -> Parameter:
        param = next(
                (p for p in sig.parameters.values() if p.annotation is dep.annotation), None
        )
        if param is None:
            to_inject.append(dep)
            param = dep
        return param
