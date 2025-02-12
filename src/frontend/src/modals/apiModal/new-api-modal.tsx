import { TweaksComponent } from "@/components/core/codeTabsComponent/components/tweaksComponent";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { CustomAPIGenerator } from "@/customization/components/custom-api-generator";
import { useCustomAPICode } from "@/customization/hooks/use-custom-api-code";
import useAuthStore from "@/stores/authStore";
import useFlowStore from "@/stores/flowStore";
import "ace-builds/src-noconflict/ext-language_tools";
import "ace-builds/src-noconflict/mode-python";
import "ace-builds/src-noconflict/theme-github";
import "ace-builds/src-noconflict/theme-twilight";
import { ReactNode, useEffect, useState } from "react";
import IconComponent from "../../components/common/genericIconComponent";
import { EXPORT_CODE_DIALOG } from "../../constants/constants";
import { useTweaksStore } from "../../stores/tweaksStore";
import { FlowType } from "../../types/flow/index";
import BaseModal from "../baseModal";
import APITabsComponent from "./codeTabs/code-tabs";

export default function ApiModal({
  children,
  open: myOpen,
  setOpen: mySetOpen,
}: {
  children: ReactNode;
  open?: boolean;
  setOpen?: (a: boolean | ((o?: boolean) => boolean)) => void;
}) {
  const autoLogin = useAuthStore((state) => state.autoLogin);
  const nodes = useFlowStore((state) => state.nodes);
  const [openTweaks, setOpenTweaks] = useState(false);
  const tweaks = useTweaksStore((state) => state.tweaks);
  const [open, setOpen] =
    mySetOpen !== undefined && myOpen !== undefined
      ? [myOpen, mySetOpen]
      : useState(false);
  const newInitialSetup = useTweaksStore((state) => state.newInitialSetup);

  useEffect(() => {
    if (open) newInitialSetup(nodes);
  }, [open]);

  return (
    <>
      <BaseModal open={open} setOpen={setOpen} size="medium" className="">
        <BaseModal.Trigger asChild>{children}</BaseModal.Trigger>
        <BaseModal.Header
          description={
            autoLogin ? undefined : (
              <>
                <span className="pr-2">
                  API access requires an API key. You can{" "}
                  <a
                    href="/settings/api-keys"
                    className="text-accent-pink-foreground"
                  >
                    {" "}
                    create an API key
                  </a>{" "}
                  in settings.
                </span>
              </>
            )
          }
        >
          <IconComponent
            name="Code2"
            className="h-6 w-6 text-gray-800 dark:text-white"
            aria-hidden="true"
          />
          <span className="pl-2">API access</span>
          {nodes.length > 0 && (
            <div className="border-r-1 absolute right-12 flex items-center text-[13px] font-medium leading-[16px]">
              <Button
                variant="ghost"
                size="icon"
                className="h-8"
                onClick={() => setOpenTweaks(true)}
              >
                <IconComponent
                  name="SlidersHorizontal"
                  className="h-3.5 w-3.5"
                />
                <span>Temporary overrides ({Object.keys(tweaks).length}) </span>
              </Button>
              <Separator orientation="vertical" className="ml-2 h-8" />
            </div>
          )}
        </BaseModal.Header>
        <BaseModal.Content overflowHidden>
          {open && (
            <>
              <CustomAPIGenerator isOpen={open} />
              <APITabsComponent />
            </>
          )}
        </BaseModal.Content>
      </BaseModal>

      <BaseModal
        open={openTweaks}
        setOpen={setOpenTweaks}
        size="medium"
        className="p-0"
      >
        <BaseModal.Content overflowHidden>
          <div className="h-full w-full overflow-y-auto overflow-x-hidden rounded-lg bg-muted pt-10 custom-scroll">
            <TweaksComponent open={openTweaks} />
          </div>
        </BaseModal.Content>
      </BaseModal>
    </>
  );
}
