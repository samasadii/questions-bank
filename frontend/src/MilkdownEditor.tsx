import { useEffect, useRef } from 'react';
import { Crepe } from '@milkdown/crepe';
import { Milkdown, MilkdownProvider, useEditor } from '@milkdown/react';
import '@milkdown/crepe/theme/common/style.css';
import '@milkdown/crepe/theme/frame.css';
import { API_BASE, getToken } from './api';

type Props = {
  value: string;
  onChange: (value: string) => void;
};

function CrepeEditor({ value, onChange }: Props) {
  const onChangeRef = useRef(onChange);
  const objectUrlsRef = useRef(new Set<string>());

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEditor((root) => {
    const crepe = new Crepe({
      root,
      defaultValue: value,
      features: {
        [Crepe.Feature.TopBar]: true,
        [Crepe.Feature.Latex]: true,
      },
      featureConfigs: {
        [Crepe.Feature.Placeholder]: {
          text: 'متن جزوه را اینجا بنویسید…',
          mode: 'block',
        },
        [Crepe.Feature.ImageBlock]: {
          proxyDomURL: async (url) => {
            if (!url.startsWith('/api/notes/')) return url;
            const response = await fetch(`${API_BASE}${url}`, {
              headers: { Authorization: `Bearer ${getToken()}` },
            });
            if (!response.ok) return url;
            const objectUrl = URL.createObjectURL(await response.blob());
            objectUrlsRef.current.add(objectUrl);
            return objectUrl;
          },
        },
      },
    });

    crepe.on((listener) => {
      listener.markdownUpdated((_ctx, markdown) => onChangeRef.current(markdown));
    });
    return crepe;
  }, []);

  useEffect(() => {
    return () => {
      objectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      objectUrlsRef.current.clear();
    };
  }, []);

  return <Milkdown />;
}

export default function MilkdownEditor(props: Props) {
  return <div className="milkdown-editor" dir="rtl">
    <MilkdownProvider>
      <CrepeEditor {...props} />
    </MilkdownProvider>
  </div>;
}
