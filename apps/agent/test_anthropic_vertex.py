from anthropic import AsyncAnthropicVertex
import inspect

spec = inspect.getfullargspec(AsyncAnthropicVertex.__init__)
print(spec.args)
print(spec.kwonlyargs)
